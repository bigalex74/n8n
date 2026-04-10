# n8n Best Practices

## 1. Architecture & Modular Design
- **Sub-workflows**: If a workflow exceeds 10-15 nodes, break it into sub-workflows using the *Execute Workflow* node.
- **Naming**: Use `[Project] [Function] - [Env]` for workflows and descriptive names for nodes (e.g., "Fetch Shopify Orders" instead of "HTTP Request").
- **Notes**: Use Sticky Notes to document the "Why" behind complex logic.

## 2. Error Handling
- **Global Error Handler**: Use a dedicated workflow with an *Error Trigger*.
- **Retries**: Enable "Retry on Fail" with Exponential Backoff for API nodes.
- **Error Routes**: Use "Continue using error output" for critical steps to handle failures gracefully.

## 3. Data Efficiency
- **Filter Early**: Remove unnecessary data as soon as possible to save memory.
- **Batches**: Use *SplitInBatches* for datasets > 100 items.
- **Bulk Operations**: Use bulk API endpoints where available.

## 4. Security
- **Credentials**: Never hardcode secrets. Always use n8n's Credential Manager.
- **Environment Variables**: Use `{{ $env["VAR"] }}` for environment-specific config.
- **Least Privilege**: Use scoped API keys.
