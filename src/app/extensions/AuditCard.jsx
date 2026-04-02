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
  hubspot,
} from "@hubspot/ui-extensions";
import { useState } from "react";

hubspot.extend(({ runServerlessFunction, context, actions }) => (
  <AuditCard runServerlessFunction={runServerlessFunction} />
));

function AuditCard({ runServerlessFunction }) {
  const [auditResult, setAuditResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runAudit = async () => {
    setLoading(true);
    setError(null);
    setAuditResult(null);

    try {
      const result = await runServerlessFunction({
        name: "runPortalAudit",
      });

      if (result.status === "SUCCESS") {
        setAuditResult(result.response);
      } else {
        setError(result.message || "Audit failed. Please try again.");
      }
    } catch (e) {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex direction="column" gap="md">
      <Text format={{ fontWeight: "bold" }}>Portal Audit</Text>
      <Text>
        Scan your portal to map dependencies between Forms, Lists, Workflows,
        and Properties. Find orphaned assets and hidden connections.
      </Text>

      <Button variant="primary" onClick={runAudit} disabled={loading}>
        {loading ? "Scanning..." : "Run Full Audit"}
      </Button>

      {loading && (
        <Flex direction="column" align="center" gap="sm">
          <LoadingSpinner />
          <Text>Scanning your portal... This may take up to 60 seconds.</Text>
        </Flex>
      )}

      {error && (
        <Alert title="Audit Error" variant="error">
          {error}
        </Alert>
      )}

      {auditResult && <AuditResults data={auditResult} />}
    </Flex>
  );
}

function AuditResults({ data }) {
  const { summary, orphanedWorkflows, orphanedLists, dependencies } = data;

  return (
    <Flex direction="column" gap="md">
      <Divider />

      <Text format={{ fontWeight: "bold" }}>Portal Summary</Text>
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Total Forms</TableCell>
            <TableCell>{summary.totalForms}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Total Lists</TableCell>
            <TableCell>{summary.totalLists}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Total Workflows</TableCell>
            <TableCell>{summary.totalWorkflows}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Total Properties</TableCell>
            <TableCell>{summary.totalProperties}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Orphaned Workflows</TableCell>
            <TableCell>
              <Tag
                variant={
                  summary.orphanedWorkflowCount > 0 ? "warning" : "success"
                }
              >
                {summary.orphanedWorkflowCount}
              </Tag>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Orphaned Lists</TableCell>
            <TableCell>
              <Tag
                variant={
                  summary.orphanedListCount > 0 ? "warning" : "success"
                }
              >
                {summary.orphanedListCount}
              </Tag>
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Unused Custom Properties</TableCell>
            <TableCell>
              <Tag
                variant={
                  summary.unusedPropertyCount > 0 ? "warning" : "success"
                }
              >
                {summary.unusedPropertyCount}
              </Tag>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <Divider />

      <Text format={{ fontWeight: "bold" }}>
        Orphaned Workflows ({orphanedWorkflows.length})
      </Text>
      {orphanedWorkflows.length === 0 ? (
        <Alert title="All clear" variant="success">
          No orphaned workflows found.
        </Alert>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Workflow</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Issue</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {orphanedWorkflows.slice(0, 20).map((wf) => (
              <TableRow key={wf.id}>
                <TableCell>{wf.name}</TableCell>
                <TableCell>
                  <Tag variant={wf.enabled ? "success" : "default"}>
                    {wf.enabled ? "Active" : "Inactive"}
                  </Tag>
                </TableCell>
                <TableCell>{wf.issue}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Divider />

      <Text format={{ fontWeight: "bold" }}>
        Orphaned Lists ({orphanedLists.length})
      </Text>
      {orphanedLists.length === 0 ? (
        <Alert title="All clear" variant="success">
          No orphaned lists found.
        </Alert>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>List</TableHeader>
              <TableHeader>Size</TableHeader>
              <TableHeader>Issue</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {orphanedLists.slice(0, 20).map((list) => (
              <TableRow key={list.id}>
                <TableCell>{list.name}</TableCell>
                <TableCell>{list.size}</TableCell>
                <TableCell>{list.issue}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Divider />

      <Text format={{ fontWeight: "bold" }}>
        Form Dependencies ({dependencies.length})
      </Text>
      {dependencies.length === 0 ? (
        <Text>No form dependencies found.</Text>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Form</TableHeader>
              <TableHeader>Lists</TableHeader>
              <TableHeader>Workflows</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {dependencies.slice(0, 30).map((dep) => (
              <TableRow key={dep.formId}>
                <TableCell>{dep.formName}</TableCell>
                <TableCell>{dep.listCount}</TableCell>
                <TableCell>{dep.workflowCount}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Flex>
  );
}
