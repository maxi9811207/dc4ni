const hubspot = require("@hubspot/api-client");

// HubSpot serverless functions receive the access token automatically
exports.main = async (context = {}) => {
  const accessToken = context.secrets?.PRIVATE_APP_ACCESS_TOKEN;

  if (!accessToken) {
    return {
      status: "ERROR",
      message: "No access token available.",
    };
  }

  const client = new hubspot.Client({ accessToken });

  try {
    const [forms, lists, workflows, properties] = await Promise.all([
      fetchAllForms(client),
      fetchAllLists(client),
      fetchAllWorkflows(client),
      fetchAllProperties(client),
    ]);

    // Build dependency map
    const dependencies = buildDependencyMap(forms, lists, workflows);

    // Find orphaned workflows (no triggers, no enrollment)
    const orphanedWorkflows = findOrphanedWorkflows(workflows);

    // Find orphaned lists (empty, not used in any workflow)
    const orphanedLists = findOrphanedLists(lists, workflows);

    // Find unused properties
    const unusedProperties = findUnusedProperties(properties, workflows);

    const summary = {
      totalForms: forms.length,
      totalLists: lists.length,
      totalWorkflows: workflows.length,
      totalProperties: properties.length,
      orphanedWorkflowCount: orphanedWorkflows.length,
      orphanedListCount: orphanedLists.length,
      unusedPropertyCount: unusedProperties.length,
    };

    return {
      status: "SUCCESS",
      response: {
        summary,
        orphanedWorkflows: orphanedWorkflows.slice(0, 50),
        orphanedLists: orphanedLists.slice(0, 50),
        unusedProperties: unusedProperties.slice(0, 50),
        dependencies: dependencies.slice(0, 100),
      },
    };
  } catch (err) {
    console.error("Audit error:", err.message);
    return {
      status: "ERROR",
      message: `Audit failed: ${err.message}`,
    };
  }
};

// ─── Data Fetching ─────────────────────────────────────────

async function fetchAllForms(client) {
  const forms = [];
  let after = undefined;

  do {
    const response = await client.apiRequest({
      method: "GET",
      path: "/marketing/v3/forms/",
      qs: { limit: 100, after },
    });
    const body = await response.json();
    forms.push(...(body.results || []));
    after = body.paging?.next?.after;
  } while (after);

  return forms;
}

async function fetchAllLists(client) {
  const lists = [];
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const response = await client.apiRequest({
      method: "GET",
      path: "/contacts/v1/lists",
      qs: { count: 250, offset },
    });
    const body = await response.json();
    lists.push(...(body.lists || []));
    hasMore = body["has-more"] || false;
    offset = body.offset || 0;
  }

  return lists;
}

async function fetchAllWorkflows(client) {
  const response = await client.apiRequest({
    method: "GET",
    path: "/automation/v4/flows",
    qs: { limit: 500 },
  });
  const body = await response.json();
  return body.results || body.flows || [];
}

async function fetchAllProperties(client) {
  const objectTypes = ["contacts", "companies", "deals"];
  const allProperties = [];

  for (const objectType of objectTypes) {
    try {
      const response =
        await client.crm.properties.coreApi.getAll(objectType);
      const props = (response.results || []).map((p) => ({
        ...p,
        objectType,
      }));
      allProperties.push(...props);
    } catch {
      // Skip if no access to this object type
    }
  }

  return allProperties;
}

// ─── Analysis Logic ────────────────────────────────────────

function buildDependencyMap(forms, lists, workflows) {
  const formDeps = forms.map((form) => {
    const formId = form.id;
    const formName = form.name || "Unnamed Form";

    // Find lists that reference this form
    const referencingLists = lists.filter((list) => {
      const filters = JSON.stringify(list.filters || list.filterBranch || {});
      return filters.includes(formId);
    });

    // Find workflows that reference this form
    const referencingWorkflows = workflows.filter((wf) => {
      const wfStr = JSON.stringify(wf);
      return wfStr.includes(formId);
    });

    return {
      formId,
      formName,
      listCount: referencingLists.length,
      workflowCount: referencingWorkflows.length,
      listNames: referencingLists.map((l) => l.name).slice(0, 5),
      workflowNames: referencingWorkflows
        .map((w) => w.name || w.flowName)
        .slice(0, 5),
    };
  });

  // Sort by most connected first
  return formDeps.sort(
    (a, b) => b.listCount + b.workflowCount - (a.listCount + a.workflowCount)
  );
}

function findOrphanedWorkflows(workflows) {
  const orphaned = [];

  for (const wf of workflows) {
    const issues = [];
    const name = wf.name || wf.flowName || "Unnamed Workflow";
    const enabled = wf.enabled ?? wf.isEnabled ?? false;

    // Check for workflows with no enrollment triggers
    const triggers = wf.enrollmentCriteria || wf.triggers || [];
    const triggerCount = Array.isArray(triggers) ? triggers.length : 0;

    if (triggerCount === 0) {
      issues.push("No enrollment triggers");
    }

    // Check for workflows with no actions
    const actions = wf.actions || wf.flowActions || [];
    const actionCount = Array.isArray(actions) ? actions.length : 0;

    if (actionCount === 0) {
      issues.push("No actions defined");
    }

    // Inactive workflows that haven't been modified in a long time
    if (!enabled && issues.length === 0) {
      issues.push("Inactive workflow");
    }

    if (issues.length > 0) {
      orphaned.push({
        id: wf.id || wf.flowId,
        name,
        enabled,
        issue: issues.join("; "),
      });
    }
  }

  return orphaned;
}

function findOrphanedLists(lists, workflows) {
  const orphaned = [];
  const workflowsStr = JSON.stringify(workflows);

  for (const list of lists) {
    const listId = String(list.listId || list.id);
    const name = list.name || "Unnamed List";
    const size = list.metaData?.size ?? list.size ?? 0;
    const issues = [];

    // Check if list is referenced in any workflow
    const usedInWorkflow = workflowsStr.includes(listId);

    if (!usedInWorkflow && size === 0) {
      issues.push("Empty list, not used in any workflow");
    } else if (!usedInWorkflow) {
      issues.push("Not used in any workflow");
    }

    // Static lists that are empty
    if (list.listType === "STATIC" && size === 0) {
      issues.push("Empty static list");
    }

    if (issues.length > 0) {
      orphaned.push({
        id: listId,
        name,
        size,
        issue: [...new Set(issues)].join("; "),
      });
    }
  }

  return orphaned;
}

function findUnusedProperties(properties, workflows) {
  const workflowsStr = JSON.stringify(workflows);
  const unused = [];

  for (const prop of properties) {
    // Only check custom properties (not HubSpot default ones)
    if (prop.hubspotDefined || prop.calculated) continue;

    const name = prop.name;
    const usedInWorkflow = workflowsStr.includes(`"${name}"`);

    if (!usedInWorkflow) {
      unused.push({
        name,
        label: prop.label,
        objectType: prop.objectType,
        type: prop.type,
        issue: "Custom property not referenced in any workflow",
      });
    }
  }

  return unused;
}
