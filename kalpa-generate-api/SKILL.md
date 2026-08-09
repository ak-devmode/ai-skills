---
name: kalpa-generate-api
description: "Generate a complete REST API endpoint following WellMed project conventions — route, controller, service, repository, types, and tests."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# Generate API Endpoint

Generate a complete REST API endpoint following project conventions.

## Arguments
- `$ARGUMENTS` - The resource name and optional actions (e.g., "patient" or "appointment --actions=create,list,cancel")

## Instructions

Create a new API endpoint for the specified resource with:

1. **Route file** at `src/api/routes/{resource}.routes.ts`:
   - Use Express Router
   - Include input validation with Zod
   - Add OpenAPI JSDoc comments

2. **Controller** at `src/api/controllers/{resource}.controller.ts`:
   - Handle HTTP concerns only
   - Delegate to service layer
   - Use standardized response format

3. **Service** at `src/services/{resource}.service.ts`:
   - Business logic here
   - Transaction handling
   - Throw custom AppError types

4. **Repository** at `src/repositories/{resource}.repository.ts`:
   - Prisma queries only
   - No business logic

5. **Types** at `src/types/{resource}.types.ts`:
   - Request/response interfaces
   - Zod schemas

6. **Tests**:
   - Unit test for service: `src/services/{resource}.service.test.ts`
   - Integration test: `__tests__/integration/{resource}.test.ts`

## Template Structure

```typescript
// routes/{resource}.routes.ts
import { Router } from 'express';
import { z } from 'zod';
import { validate } from '@/middleware/validate';
import { {Resource}Controller } from '@/controllers/{resource}.controller';

const router = Router();
const controller = new {Resource}Controller();

/**
 * @openapi
 * /api/v1/{resource}:
 *   post:
 *     summary: Create a new {resource}
 *     tags: [{Resource}]
 */
router.post('/', validate(create{Resource}Schema), controller.create);

export default router;
```

## Response Format

All endpoints must return:
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "requestId": "uuid",
    "timestamp": "ISO8601"
  }
}
```

Or on error:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": []
  }
}
```
