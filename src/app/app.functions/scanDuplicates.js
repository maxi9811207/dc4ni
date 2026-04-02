const hubspot = require("@hubspot/api-client");

exports.main = async (context = {}) => {
  const accessToken = context.secrets?.PRIVATE_APP_ACCESS_TOKEN;
  if (!accessToken) {
    return { status: "ERROR", message: "No access token." };
  }

  const client = new hubspot.Client({ accessToken });
  const objectType = context.parameters?.objectType || "contacts";

  try {
    // Fetch contacts in batches for duplicate analysis
    const records = await fetchRecords(client, objectType);
    const pairs = findDuplicates(records);

    return {
      status: "SUCCESS",
      response: {
        totalRecordsScanned: records.length,
        pairs: pairs.slice(0, 50),
      },
    };
  } catch (err) {
    console.error("Duplicate scan error:", err.message);
    return { status: "ERROR", message: `Scan failed: ${err.message}` };
  }
};

async function fetchRecords(client, objectType) {
  const records = [];
  let after = undefined;
  const maxPages = 10; // Scan up to 1000 records (serverless 10s timeout)
  let page = 0;

  const properties =
    objectType === "contacts"
      ? ["email", "firstname", "lastname", "phone", "company"]
      : ["name", "domain", "phone"];

  while (page < maxPages) {
    const response = await client.crm[objectType].basicApi.getPage(
      100,
      after,
      properties
    );

    for (const record of response.results || []) {
      records.push({
        id: record.id,
        email: record.properties.email || "",
        firstName: record.properties.firstname || "",
        lastName: record.properties.lastname || "",
        name:
          objectType === "contacts"
            ? `${record.properties.firstname || ""} ${record.properties.lastname || ""}`.trim()
            : record.properties.name || "",
        phone: normalizePhone(record.properties.phone || ""),
        company: record.properties.company || "",
        domain: record.properties.domain || "",
      });
    }

    after = response.paging?.next?.after;
    if (!after) break;
    page++;
  }

  return records;
}

function findDuplicates(records) {
  const pairs = [];
  const seen = new Set();

  // Index by email for fast lookup
  const emailIndex = {};
  for (const r of records) {
    if (r.email) {
      const key = r.email.toLowerCase().trim();
      if (!emailIndex[key]) emailIndex[key] = [];
      emailIndex[key].push(r);
    }
  }

  // Find exact email duplicates
  for (const [email, group] of Object.entries(emailIndex)) {
    if (group.length > 1) {
      for (let i = 0; i < group.length - 1; i++) {
        const pairKey = `${group[i].id}-${group[i + 1].id}`;
        if (!seen.has(pairKey)) {
          seen.add(pairKey);
          pairs.push({
            a: { id: group[i].id, name: group[i].name, email: group[i].email },
            b: {
              id: group[i + 1].id,
              name: group[i + 1].name,
              email: group[i + 1].email,
            },
            confidence: "high",
            matchReason: "exact email",
          });
        }
      }
    }
  }

  // Index by phone for duplicates
  const phoneIndex = {};
  for (const r of records) {
    if (r.phone && r.phone.length >= 7) {
      const key = r.phone;
      if (!phoneIndex[key]) phoneIndex[key] = [];
      phoneIndex[key].push(r);
    }
  }

  for (const [phone, group] of Object.entries(phoneIndex)) {
    if (group.length > 1) {
      for (let i = 0; i < group.length - 1; i++) {
        const pairKey = [group[i].id, group[i + 1].id].sort().join("-");
        if (!seen.has(pairKey)) {
          seen.add(pairKey);
          pairs.push({
            a: { id: group[i].id, name: group[i].name, email: group[i].email },
            b: {
              id: group[i + 1].id,
              name: group[i + 1].name,
              email: group[i + 1].email,
            },
            confidence: "high",
            matchReason: "exact phone",
          });
        }
      }
    }
  }

  // Fuzzy name matching (simple Levenshtein-based)
  for (let i = 0; i < records.length && i < 500; i++) {
    for (let j = i + 1; j < records.length && j < 500; j++) {
      const a = records[i];
      const b = records[j];

      const pairKey = [a.id, b.id].sort().join("-");
      if (seen.has(pairKey)) continue;

      // Same name, different records
      if (
        a.name &&
        b.name &&
        a.name.length > 2 &&
        a.name.toLowerCase() === b.name.toLowerCase()
      ) {
        // Additional signal: same company or similar email domain
        const sameCompany =
          a.company &&
          b.company &&
          a.company.toLowerCase() === b.company.toLowerCase();
        const sameEmailDomain =
          a.email &&
          b.email &&
          getEmailDomain(a.email) === getEmailDomain(b.email);

        if (sameCompany || sameEmailDomain) {
          seen.add(pairKey);
          pairs.push({
            a: { id: a.id, name: a.name, email: a.email },
            b: { id: b.id, name: b.name, email: b.email },
            confidence: "medium",
            matchReason: sameCompany
              ? "same name + company"
              : "same name + email domain",
          });
        }
      }
    }
  }

  // Sort by confidence (high first)
  return pairs.sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.confidence] || 2) - (order[b.confidence] || 2);
  });
}

function normalizePhone(phone) {
  return phone.replace(/[\s\-\(\)\+\.]/g, "");
}

function getEmailDomain(email) {
  const parts = email.toLowerCase().split("@");
  return parts.length === 2 ? parts[1] : "";
}
