---
name: kalpa-coding-standards
description: "WellMed coding standards — TypeScript patterns for service layer, repository, error handling, Zod validation, and testing. Use when writing or reviewing WellMed application code."
allowed-tools:
  - Read
  - Glob
  - Grep
---

# WellMed Coding Standards Skill

## TypeScript Patterns

### Service Layer Pattern
```typescript
// ✅ Correct: Services handle business logic and transactions
export class AppointmentService {
  constructor(
    private readonly appointmentRepo: AppointmentRepository,
    private readonly patientRepo: PatientRepository,
    private readonly notificationService: NotificationService,
  ) {}

  async createAppointment(data: CreateAppointmentInput): Promise<Appointment> {
    // Validate business rules
    const patient = await this.patientRepo.findById(data.patientId);
    if (!patient) {
      throw new NotFoundError('PATIENT_NOT_FOUND', 'Patient does not exist');
    }

    // Check for conflicts
    const conflicts = await this.appointmentRepo.findConflicting(
      data.practitionerId,
      data.startTime,
      data.endTime,
    );
    if (conflicts.length > 0) {
      throw new ConflictError('SLOT_UNAVAILABLE', 'Time slot is not available');
    }

    // Create with transaction
    const appointment = await this.appointmentRepo.create(data);

    // Side effects
    await this.notificationService.sendAppointmentConfirmation(appointment);

    return appointment;
  }
}
```

### Repository Pattern
```typescript
// ✅ Correct: Repositories are data access only
export class AppointmentRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: string): Promise<Appointment | null> {
    return this.prisma.appointment.findUnique({
      where: { id },
      include: {
        patient: true,
        practitioner: true,
      },
    });
  }

  async findConflicting(
    practitionerId: string,
    startTime: Date,
    endTime: Date,
  ): Promise<Appointment[]> {
    return this.prisma.appointment.findMany({
      where: {
        practitionerId,
        status: { not: 'CANCELLED' },
        OR: [
          { startTime: { gte: startTime, lt: endTime } },
          { endTime: { gt: startTime, lte: endTime } },
          {
            AND: [
              { startTime: { lte: startTime } },
              { endTime: { gte: endTime } },
            ],
          },
        ],
      },
    });
  }
}
```

### Error Handling
```typescript
// Custom error classes
export class AppError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number = 500,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class NotFoundError extends AppError {
  constructor(code: string, message: string) {
    super(code, message, 404);
  }
}

export class ValidationError extends AppError {
  constructor(code: string, message: string, details?: ZodError) {
    super(code, message, 400, details?.errors);
  }
}

export class ConflictError extends AppError {
  constructor(code: string, message: string) {
    super(code, message, 409);
  }
}

// Error handler middleware
export const errorHandler: ErrorRequestHandler = (err, req, res, next) => {
  const logger = req.log || console;

  if (err instanceof AppError) {
    logger.warn({ err, code: err.code }, err.message);
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message,
        details: err.details,
      },
    });
  }

  // Unexpected errors
  logger.error({ err }, 'Unhandled error');
  return res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
    },
  });
};
```

### Zod Validation
```typescript
import { z } from 'zod';

// Define schemas
export const createAppointmentSchema = z.object({
  patientId: z.string().uuid(),
  practitionerId: z.string().uuid(),
  startTime: z.string().datetime(),
  endTime: z.string().datetime(),
  type: z.enum(['CONSULTATION', 'FOLLOW_UP', 'PROCEDURE']),
  notes: z.string().max(1000).optional(),
}).refine(
  (data) => new Date(data.endTime) > new Date(data.startTime),
  { message: 'End time must be after start time', path: ['endTime'] },
);

export type CreateAppointmentInput = z.infer<typeof createAppointmentSchema>;

// Validation middleware
export const validate = <T extends z.ZodSchema>(schema: T) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      throw new ValidationError(
        'VALIDATION_ERROR',
        'Invalid request data',
        result.error,
      );
    }
    req.body = result.data;
    next();
  };
};
```

## Testing Patterns

### Unit Tests
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('AppointmentService', () => {
  let service: AppointmentService;
  let mockAppointmentRepo: MockedObject<AppointmentRepository>;
  let mockPatientRepo: MockedObject<PatientRepository>;

  beforeEach(() => {
    mockAppointmentRepo = {
      findById: vi.fn(),
      findConflicting: vi.fn(),
      create: vi.fn(),
    };
    mockPatientRepo = {
      findById: vi.fn(),
    };

    service = new AppointmentService(
      mockAppointmentRepo,
      mockPatientRepo,
      mockNotificationService,
    );
  });

  describe('createAppointment', () => {
    it('should create appointment when slot is available', async () => {
      // Arrange
      const input = createAppointmentInputFactory();
      mockPatientRepo.findById.mockResolvedValue(patientFactory());
      mockAppointmentRepo.findConflicting.mockResolvedValue([]);
      mockAppointmentRepo.create.mockResolvedValue(appointmentFactory());

      // Act
      const result = await service.createAppointment(input);

      // Assert
      expect(result).toBeDefined();
      expect(mockAppointmentRepo.create).toHaveBeenCalledWith(input);
    });

    it('should throw ConflictError when slot is taken', async () => {
      // Arrange
      mockPatientRepo.findById.mockResolvedValue(patientFactory());
      mockAppointmentRepo.findConflicting.mockResolvedValue([appointmentFactory()]);

      // Act & Assert
      await expect(service.createAppointment(createAppointmentInputFactory()))
        .rejects.toThrow(ConflictError);
    });
  });
});
```

### Integration Tests
```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createTestApp, createTestDatabase } from '@/test/helpers';

describe('POST /api/v1/appointments', () => {
  let app: Express;
  let db: TestDatabase;

  beforeAll(async () => {
    db = await createTestDatabase();
    app = createTestApp(db.prisma);
  });

  afterAll(async () => {
    await db.cleanup();
  });

  it('should create appointment and return 201', async () => {
    // Seed test data
    const patient = await db.createPatient();
    const practitioner = await db.createPractitioner();

    // Make request
    const response = await request(app)
      .post('/api/v1/appointments')
      .send({
        patientId: patient.id,
        practitionerId: practitioner.id,
        startTime: '2024-01-15T09:00:00+07:00',
        endTime: '2024-01-15T09:30:00+07:00',
        type: 'CONSULTATION',
      });

    // Assertions
    expect(response.status).toBe(201);
    expect(response.body.success).toBe(true);
    expect(response.body.data.id).toBeDefined();
  });
});
```
