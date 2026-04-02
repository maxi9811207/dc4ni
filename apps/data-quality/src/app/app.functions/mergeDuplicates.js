const hubspot = require("@hubspot/api-client");

exports.main = async (context = {}) => {
  const accessToken = context.secrets?.PRIVATE_APP_ACCESS_TOKEN;
  if (!accessToken) {
    return { status: "ERROR", message: "No access token." };
  }

  const client = new hubspot.Client({ accessToken });
  const { objectType, primaryId, secondaryId } = context.parameters || {};

  if (!primaryId || !secondaryId) {
    return { status: "ERROR", message: "Missing primaryId or secondaryId." };
  }

  try {
    // HubSpot merge API: merges secondaryId INTO primaryId
    // The primary record survives; the secondary is deleted
    await client.apiRequest({
      method: "POST",
      path: `/crm/v3/objects/${objectType || "contacts"}/merge`,
      body: {
        primaryObjectId: primaryId,
        objectIdToMerge: secondaryId,
      },
    });

    return {
      status: "SUCCESS",
      response: {
        merged: true,
        survivingId: primaryId,
        mergedId: secondaryId,
      },
    };
  } catch (err) {
    console.error("Merge error:", err.message);
    return { status: "ERROR", message: `Merge failed: ${err.message}` };
  }
};
