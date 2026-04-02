const hubspot = require("@hubspot/api-client");

exports.main = async (context = {}) => {
  const accessToken = context.secrets?.PRIVATE_APP_ACCESS_TOKEN;
  if (!accessToken) {
    return { status: "ERROR", message: "No access token." };
  }

  const client = new hubspot.Client({ accessToken });
  const objectType = context.parameters?.objectType || "contacts";

  try {
    const records = await fetchSample(client, objectType);
    const score = calculateScore(records, objectType);

    return { status: "SUCCESS", response: score };
  } catch (err) {
    console.error("Health score error:", err.message);
    return {
      status: "ERROR",
      message: `Health score failed: ${err.message}`,
    };
  }
};

async function fetchSample(client, objectType) {
  const properties =
    objectType === "contacts"
      ? [
          "email",
          "firstname",
          "lastname",
          "phone",
          "company",
          "jobtitle",
          "city",
          "state",
          "country",
          "lifecyclestage",
        ]
      : [
          "name",
          "domain",
          "phone",
          "city",
          "state",
          "country",
          "industry",
          "numberofemployees",
        ];

  const records = [];
  let after = undefined;
  let page = 0;

  while (page < 5) {
    const response = await client.crm[objectType].basicApi.getPage(
      100,
      after,
      properties
    );
    records.push(...(response.results || []));
    after = response.paging?.next?.after;
    if (!after) break;
    page++;
  }

  return records;
}

function calculateScore(records, objectType) {
  if (records.length === 0) {
    return {
      overall: 100,
      categories: [
        {
          name: "No Data",
          score: 100,
          recommendation: "No records found to analyze.",
        },
      ],
    };
  }

  const categories = [];

  // 1. Completeness: how many key fields are filled?
  const completeness = measureCompleteness(records, objectType);
  categories.push(completeness);

  // 2. Consistency: are formats consistent?
  const consistency = measureConsistency(records, objectType);
  categories.push(consistency);

  // 3. Duplicates estimate: based on email/name overlap
  const duplicateRisk = estimateDuplicateRisk(records, objectType);
  categories.push(duplicateRisk);

  // 4. Freshness: lifecycle stage distribution
  if (objectType === "contacts") {
    const freshness = measureFreshness(records);
    categories.push(freshness);
  }

  const overall = Math.round(
    categories.reduce((sum, c) => sum + c.score, 0) / categories.length
  );

  return { overall, categories, totalRecordsAnalyzed: records.length };
}

function measureCompleteness(records, objectType) {
  const keyFields =
    objectType === "contacts"
      ? ["email", "firstname", "lastname", "phone", "company"]
      : ["name", "domain", "phone", "industry"];

  let totalFilled = 0;
  let totalChecks = 0;

  for (const record of records) {
    for (const field of keyFields) {
      totalChecks++;
      const val = record.properties[field];
      if (val && val.trim() !== "") totalFilled++;
    }
  }

  const pct = totalChecks > 0 ? Math.round((totalFilled / totalChecks) * 100) : 100;
  const emptyPct = 100 - pct;

  let recommendation = "Excellent data completeness.";
  if (pct < 50) {
    recommendation = `${emptyPct}% of key fields are empty. Focus on enriching email and company data.`;
  } else if (pct < 80) {
    recommendation = `${emptyPct}% of key fields are empty. Consider adding phone and job title data.`;
  }

  return { name: "Completeness", score: pct, recommendation };
}

function measureConsistency(records, objectType) {
  let issues = 0;
  let total = 0;

  for (const record of records) {
    const props = record.properties;

    // Check name casing consistency
    if (props.firstname) {
      total++;
      if (props.firstname !== toTitleCase(props.firstname)) issues++;
    }
    if (props.lastname) {
      total++;
      if (props.lastname !== toTitleCase(props.lastname)) issues++;
    }

    // Check email format
    if (props.email) {
      total++;
      if (props.email !== props.email.trim().toLowerCase()) issues++;
    }

    // Check for extra whitespace
    for (const val of Object.values(props)) {
      if (typeof val === "string" && val !== val.trim()) {
        issues++;
      }
    }
  }

  const score = total > 0 ? Math.round(((total - issues) / total) * 100) : 100;

  let recommendation = "Data formatting is consistent.";
  if (score < 50) {
    recommendation = `${issues} formatting issues found. Run Data Cleanup to fix casing, emails, and whitespace.`;
  } else if (score < 80) {
    recommendation = `${issues} minor formatting issues. Run Data Cleanup for a quick fix.`;
  }

  return { name: "Consistency", score, recommendation };
}

function estimateDuplicateRisk(records, objectType) {
  const emailCounts = {};
  const nameCounts = {};

  for (const record of records) {
    const email = (record.properties.email || "").toLowerCase().trim();
    if (email) {
      emailCounts[email] = (emailCounts[email] || 0) + 1;
    }

    const name =
      objectType === "contacts"
        ? `${record.properties.firstname || ""} ${record.properties.lastname || ""}`
            .trim()
            .toLowerCase()
        : (record.properties.name || "").toLowerCase();

    if (name && name.length > 2) {
      nameCounts[name] = (nameCounts[name] || 0) + 1;
    }
  }

  const emailDupes = Object.values(emailCounts).filter((c) => c > 1).length;
  const nameDupes = Object.values(nameCounts).filter((c) => c > 1).length;
  const totalDupes = emailDupes + nameDupes;

  const dupeRate = records.length > 0 ? totalDupes / records.length : 0;
  const score = Math.max(0, Math.round((1 - dupeRate * 5) * 100));

  let recommendation = "Low duplicate risk.";
  if (score < 50) {
    recommendation = `High risk: ~${emailDupes} email dupes, ~${nameDupes} name dupes detected. Run Duplicate Scanner now.`;
  } else if (score < 80) {
    recommendation = `Moderate risk: ${totalDupes} potential duplicates found. Review recommended.`;
  }

  return { name: "Duplicate Risk", score, recommendation };
}

function measureFreshness(records) {
  const stages = {};
  for (const record of records) {
    const stage = record.properties.lifecyclestage || "unknown";
    stages[stage] = (stages[stage] || 0) + 1;
  }

  const total = records.length;
  const unknownPct = ((stages.unknown || 0) / total) * 100;

  // High % of records without lifecycle stage = poor hygiene
  const score = Math.max(0, Math.round(100 - unknownPct));

  let recommendation = "Lifecycle stages are well-maintained.";
  if (score < 50) {
    recommendation = `${Math.round(unknownPct)}% of contacts have no lifecycle stage. Set up lifecycle stage automation.`;
  } else if (score < 80) {
    recommendation = `${Math.round(unknownPct)}% of contacts lack lifecycle stages. Consider cleanup.`;
  }

  return { name: "Lifecycle Freshness", score, recommendation };
}

function toTitleCase(str) {
  return str
    .toLowerCase()
    .split(" ")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : ""))
    .join(" ");
}
