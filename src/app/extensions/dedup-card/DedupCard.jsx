import {
  Flex,
  Text,
  Button,
  Alert,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  LoadingSpinner,
  Divider,
  Tag,
  Tabs,
  Tab,
  Select,
  hubspot,
} from "@hubspot/ui-extensions";
import { useState } from "react";

hubspot.extend(({ runServerlessFunction, context }) => (
  <DedupCard
    runServerlessFunction={runServerlessFunction}
    objectType={context.crm.objectType}
    objectId={context.crm.objectId}
  />
));

function DedupCard({ runServerlessFunction, objectType, objectId }) {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Flex direction="column" gap="md">
      <Text format={{ fontWeight: "bold" }}>Data Quality Pro</Text>
      <Tabs
        onTabChange={(tabIndex) => setActiveTab(tabIndex)}
        defaultTabIndex={0}
      >
        <Tab label="Duplicates">
          <DuplicateScanner
            runServerlessFunction={runServerlessFunction}
            objectType={objectType}
          />
        </Tab>
        <Tab label="Data Cleanup">
          <DataCleanup
            runServerlessFunction={runServerlessFunction}
            objectType={objectType}
          />
        </Tab>
        <Tab label="Health Score">
          <HealthScore
            runServerlessFunction={runServerlessFunction}
            objectType={objectType}
          />
        </Tab>
      </Tabs>
    </Flex>
  );
}

// ─── Tab 1: Duplicate Scanner ──────────────────────────────

function DuplicateScanner({ runServerlessFunction, objectType }) {
  const [duplicates, setDuplicates] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mergeStatus, setMergeStatus] = useState({});

  const scanForDuplicates = async () => {
    setLoading(true);
    setError(null);
    setDuplicates(null);

    try {
      const result = await runServerlessFunction({
        name: "scanDuplicates",
        parameters: { objectType: objectType || "contacts" },
      });

      if (result.status === "SUCCESS") {
        setDuplicates(result.response);
      } else {
        setError(result.message || "Scan failed.");
      }
    } catch {
      setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const mergePair = async (primaryId, secondaryId, pairIndex) => {
    setMergeStatus((prev) => ({ ...prev, [pairIndex]: "merging" }));

    try {
      const result = await runServerlessFunction({
        name: "mergeDuplicates",
        parameters: {
          objectType: objectType || "contacts",
          primaryId,
          secondaryId,
        },
      });

      if (result.status === "SUCCESS") {
        setMergeStatus((prev) => ({ ...prev, [pairIndex]: "merged" }));
      } else {
        setMergeStatus((prev) => ({ ...prev, [pairIndex]: "error" }));
      }
    } catch {
      setMergeStatus((prev) => ({ ...prev, [pairIndex]: "error" }));
    }
  };

  return (
    <Flex direction="column" gap="md">
      <Text>
        Find duplicate contacts using fuzzy matching on email, name, phone, and
        company.
      </Text>

      <Button variant="primary" onClick={scanForDuplicates} disabled={loading}>
        {loading ? "Scanning..." : "Scan for Duplicates"}
      </Button>

      {loading && (
        <Flex direction="column" align="center" gap="sm">
          <LoadingSpinner />
          <Text>Analyzing contacts for duplicates...</Text>
        </Flex>
      )}

      {error && (
        <Alert title="Scan Error" variant="error">
          {error}
        </Alert>
      )}

      {duplicates && (
        <Flex direction="column" gap="sm">
          <Alert
            title={`Found ${duplicates.pairs.length} duplicate pairs`}
            variant={duplicates.pairs.length > 0 ? "warning" : "success"}
          >
            {duplicates.pairs.length > 0
              ? `${duplicates.totalRecordsScanned} records scanned. Review and merge below.`
              : `${duplicates.totalRecordsScanned} records scanned. No duplicates found!`}
          </Alert>

          {duplicates.pairs.length > 0 && (
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Record A</TableHeader>
                  <TableHeader>Record B</TableHeader>
                  <TableHeader>Match</TableHeader>
                  <TableHeader>Action</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {duplicates.pairs.slice(0, 25).map((pair, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      {pair.a.name}
                      {pair.a.email ? ` (${pair.a.email})` : ""}
                    </TableCell>
                    <TableCell>
                      {pair.b.name}
                      {pair.b.email ? ` (${pair.b.email})` : ""}
                    </TableCell>
                    <TableCell>
                      <Tag
                        variant={
                          pair.confidence === "high" ? "error" : "warning"
                        }
                      >
                        {pair.confidence} ({pair.matchReason})
                      </Tag>
                    </TableCell>
                    <TableCell>
                      {mergeStatus[idx] === "merged" ? (
                        <Tag variant="success">Merged</Tag>
                      ) : mergeStatus[idx] === "merging" ? (
                        <Text>Merging...</Text>
                      ) : mergeStatus[idx] === "error" ? (
                        <Tag variant="error">Failed</Tag>
                      ) : (
                        <Button
                          variant="secondary"
                          size="small"
                          onClick={() => mergePair(pair.a.id, pair.b.id, idx)}
                        >
                          Merge
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Flex>
      )}
    </Flex>
  );
}

// ─── Tab 2: Data Cleanup ───────────────────────────────────

function DataCleanup({ runServerlessFunction, objectType }) {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runCleanup = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await runServerlessFunction({
        name: "runDataCleanup",
        parameters: { objectType: objectType || "contacts", dryRun: true },
      });

      if (result.status === "SUCCESS") {
        setResults(result.response);
      } else {
        setError(result.message || "Cleanup scan failed.");
      }
    } catch {
      setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const applyFixes = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await runServerlessFunction({
        name: "runDataCleanup",
        parameters: { objectType: objectType || "contacts", dryRun: false },
      });

      if (result.status === "SUCCESS") {
        setResults(result.response);
      } else {
        setError(result.message || "Cleanup failed.");
      }
    } catch {
      setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex direction="column" gap="md">
      <Text>
        Standardize phone numbers, fix name casing, normalize emails, and clean
        up empty fields.
      </Text>

      <Button variant="primary" onClick={runCleanup} disabled={loading}>
        {loading ? "Scanning..." : "Preview Cleanup"}
      </Button>

      {loading && (
        <Flex direction="column" align="center" gap="sm">
          <LoadingSpinner />
          <Text>Analyzing data quality issues...</Text>
        </Flex>
      )}

      {error && (
        <Alert title="Error" variant="error">
          {error}
        </Alert>
      )}

      {results && (
        <Flex direction="column" gap="sm">
          <Text format={{ fontWeight: "bold" }}>
            Issues Found: {results.totalIssues}
          </Text>

          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Issue Type</TableHeader>
                <TableHeader>Count</TableHeader>
                <TableHeader>Example</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.issuesByType.map((issue) => (
                <TableRow key={issue.type}>
                  <TableCell>{issue.label}</TableCell>
                  <TableCell>{issue.count}</TableCell>
                  <TableCell>
                    {issue.example
                      ? `"${issue.example.before}" → "${issue.example.after}"`
                      : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {results.dryRun && results.totalIssues > 0 && (
            <Button variant="primary" onClick={applyFixes} disabled={loading}>
              Apply All Fixes ({results.totalIssues} changes)
            </Button>
          )}

          {!results.dryRun && (
            <Alert title="Cleanup Complete" variant="success">
              {results.totalFixed} records updated successfully.
            </Alert>
          )}
        </Flex>
      )}
    </Flex>
  );
}

// ─── Tab 3: Health Score ───────────────────────────────────

function HealthScore({ runServerlessFunction, objectType }) {
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const calculateScore = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await runServerlessFunction({
        name: "calculateHealthScore",
        parameters: { objectType: objectType || "contacts" },
      });

      if (result.status === "SUCCESS") {
        setScore(result.response);
      } else {
        setError(result.message || "Failed to calculate health score.");
      }
    } catch {
      setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex direction="column" gap="md">
      <Text>
        Get an overall health score for your CRM data quality, with specific
        recommendations.
      </Text>

      <Button variant="primary" onClick={calculateScore} disabled={loading}>
        {loading ? "Calculating..." : "Calculate Health Score"}
      </Button>

      {loading && <LoadingSpinner />}

      {error && (
        <Alert title="Error" variant="error">
          {error}
        </Alert>
      )}

      {score && (
        <Flex direction="column" gap="sm">
          <Flex direction="row" align="center" gap="md">
            <Text format={{ fontWeight: "bold" }}>
              Overall Score: {score.overall}/100
            </Text>
            <Tag
              variant={
                score.overall >= 80
                  ? "success"
                  : score.overall >= 50
                    ? "warning"
                    : "error"
              }
            >
              {score.overall >= 80
                ? "Healthy"
                : score.overall >= 50
                  ? "Needs Work"
                  : "Critical"}
            </Tag>
          </Flex>

          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Category</TableHeader>
                <TableHeader>Score</TableHeader>
                <TableHeader>Issue</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {score.categories.map((cat) => (
                <TableRow key={cat.name}>
                  <TableCell>{cat.name}</TableCell>
                  <TableCell>
                    <Tag
                      variant={
                        cat.score >= 80
                          ? "success"
                          : cat.score >= 50
                            ? "warning"
                            : "error"
                      }
                    >
                      {cat.score}/100
                    </Tag>
                  </TableCell>
                  <TableCell>{cat.recommendation}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Flex>
      )}
    </Flex>
  );
}
