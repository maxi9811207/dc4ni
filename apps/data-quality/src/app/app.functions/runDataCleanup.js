const hubspot = require("@hubspot/api-client");

exports.main = async (context = {}) => {
  const accessToken = context.secrets?.PRIVATE_APP_ACCESS_TOKEN;
  if (!accessToken) {
    return { status: "ERROR", message: "No access token." };
  }

  const client = new hubspot.Client({ accessToken });
  const { objectType = "contacts", dryRun = true } = context.parameters || {};

  try {
    const records = await fetchRecords(client, objectType);
    const issues = analyzeIssues(records);

    if (dryRun) {
      return {
        status: "SUCCESS",
        response: {
          dryRun: true,
          totalIssues: issues.totalIssues,
          issuesByType: issues.summary,
        },
      };
    }

    // Apply fixes
    const fixed = await applyFixes(client, objectType, issues.fixes);

    return {
      status: "SUCCESS",
      response: {
        dryRun: false,
        totalFixed: fixed,
        totalIssues: issues.totalIssues,
        issuesByType: issues.summary,
      },
    };
  } catch (err) {
    console.error("Cleanup error:", err.message);
    return { status: "ERROR", message: `Cleanup failed: ${err.message}` };
  }
};

async function fetchRecords(client, objectType) {
  const records = [];
  let after = undefined;
  const maxPages = 5;
  let page = 0;

  const properties =
    objectType === "contacts"
      ? ["email", "firstname", "lastname", "phone", "company", "city", "state"]
      : ["name", "domain", "phone", "city", "state"];

  while (page < maxPages) {
    const response = await client.crm[objectType].basicApi.getPage(
      100,
      after,
      properties
    );

    for (const record of response.results || []) {
      records.push({
        id: record.id,
        properties: record.properties,
      });
    }

    after = response.paging?.next?.after;
    if (!after) break;
    page++;
  }

  return records;
}

function analyzeIssues(records) {
  const fixes = [];
  const counts = {
    nameCase: 0,
    emailFormat: 0,
    phoneFormat: 0,
    emptyFields: 0,
    whitespace: 0,
  };
  const examples = {};

  for (const record of records) {
    const props = record.properties;
    const recordFixes = {};

    // Fix name casing: "john doe" → "John Doe"
    for (const field of ["firstname", "lastname"]) {
      const val = props[field];
      if (val && val !== toTitleCase(val)) {
        const fixed = toTitleCase(val);
        recordFixes[field] = fixed;
        counts.nameCase++;
        if (!examples.nameCase) {
          examples.nameCase = { before: val, after: fixed };
        }
      }
    }

    // Fix email: remove leading/trailing whitespace, lowercase
    if (props.email) {
      const cleaned = props.email.trim().toLowerCase();
      if (cleaned !== props.email) {
        recordFixes.email = cleaned;
        counts.emailFormat++;
        if (!examples.emailFormat) {
          examples.emailFormat = { before: props.email, after: cleaned };
        }
      }
    }

    // Standardize phone: remove extra spaces, add formatting
    if (props.phone) {
      const cleaned = standardizePhone(props.phone);
      if (cleaned !== props.phone) {
        recordFixes.phone = cleaned;
        counts.phoneFormat++;
        if (!examples.phoneFormat) {
          examples.phoneFormat = { before: props.phone, after: cleaned };
        }
      }
    }

    // Trim whitespace from all text fields
    for (const [key, val] of Object.entries(props)) {
      if (typeof val === "string" && val !== val.trim() && !recordFixes[key]) {
        recordFixes[key] = val.trim();
        counts.whitespace++;
        if (!examples.whitespace) {
          examples.whitespace = { before: `"${val}"`, after: `"${val.trim()}"` };
        }
      }
    }

    if (Object.keys(recordFixes).length > 0) {
      fixes.push({ id: record.id, properties: recordFixes });
    }
  }

  const summary = [
    {
      type: "nameCase",
      label: "Name Casing (john → John)",
      count: counts.nameCase,
      example: examples.nameCase || null,
    },
    {
      type: "emailFormat",
      label: "Email Format (trim + lowercase)",
      count: counts.emailFormat,
      example: examples.emailFormat || null,
    },
    {
      type: "phoneFormat",
      label: "Phone Standardization",
      count: counts.phoneFormat,
      example: examples.phoneFormat || null,
    },
    {
      type: "whitespace",
      label: "Extra Whitespace",
      count: counts.whitespace,
      example: examples.whitespace || null,
    },
  ].filter((s) => s.count > 0);

  return {
    totalIssues: fixes.length,
    summary,
    fixes,
  };
}

async function applyFixes(client, objectType, fixes) {
  let fixed = 0;

  // Batch update in groups of 100
  for (let i = 0; i < fixes.length; i += 100) {
    const batch = fixes.slice(i, i + 100);

    try {
      await client.crm[objectType].batchApi.update({
        inputs: batch.map((f) => ({
          id: f.id,
          properties: f.properties,
        })),
      });
      fixed += batch.length;
    } catch (err) {
      console.error(`Batch update failed at offset ${i}:`, err.message);
    }
  }

  return fixed;
}

function toTitleCase(str) {
  return str
    .toLowerCase()
    .split(" ")
    .map((word) => (word.length > 0 ? word[0].toUpperCase() + word.slice(1) : ""))
    .join(" ");
}

function standardizePhone(phone) {
  // Remove all non-digit chars except leading +
  const hasPlus = phone.startsWith("+");
  const digits = phone.replace(/\D/g, "");

  if (digits.length === 0) return phone;

  // Return cleaned version with original + prefix if present
  if (hasPlus) {
    return "+" + digits;
  }
  return digits;
}
