---
name: kalpa-satu-sehat-fhir
description: "SATU SEHAT FHIR validation — validate FHIR Bundle structure, Indonesian healthcare identifiers (NIK, IHS), ICD-10/LOINC coding, and common integration errors."
allowed-tools:
  - Read
  - Glob
  - Grep
---

# SATU SEHAT FHIR Validation Skill

## Overview
This skill provides expertise in validating FHIR resources for Indonesia's SATU SEHAT healthcare integration system.

## Capabilities
- Validate FHIR Bundle structure
- Check required Indonesian healthcare identifiers
- Verify ICD-10 and ICD-9-CM coding
- Ensure LOINC codes for lab results
- Validate organization and practitioner references

## FHIR Resource Requirements

### Patient Resource
```json
{
  "resourceType": "Patient",
  "identifier": [
    {
      "use": "official",
      "system": "https://fhir.kemkes.go.id/id/nik",
      "value": "3374010101900001"  // 16-digit NIK required
    },
    {
      "use": "official",
      "system": "https://fhir.kemkes.go.id/id/ihs-number",
      "value": "P12345678"  // IHS number from SATU SEHAT
    }
  ],
  "name": [{ "text": "Full Name", "use": "official" }],
  "birthDate": "1990-01-01",  // Required
  "gender": "male"  // male | female | other | unknown
}
```

### Encounter Resource
```json
{
  "resourceType": "Encounter",
  "status": "finished",
  "class": {
    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
    "code": "AMB"  // AMB=outpatient, IMP=inpatient, EMER=emergency
  },
  "subject": { "reference": "Patient/{ihs-number}" },
  "participant": [{
    "individual": { "reference": "Practitioner/{ihs-number}" }
  }],
  "period": {
    "start": "2024-01-15T09:00:00+07:00",
    "end": "2024-01-15T09:30:00+07:00"
  },
  "serviceProvider": { "reference": "Organization/{org-id}" }
}
```

### Condition (Diagnosis)
```json
{
  "resourceType": "Condition",
  "clinicalStatus": {
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
      "code": "active"
    }]
  },
  "code": {
    "coding": [{
      "system": "http://hl7.org/fhir/sid/icd-10",
      "code": "J06.9",
      "display": "Acute upper respiratory infection, unspecified"
    }]
  },
  "subject": { "reference": "Patient/{ihs-number}" },
  "encounter": { "reference": "Encounter/{uuid}" }
}
```

## Common Validation Errors

| Error Code | Description | Fix |
|------------|-------------|-----|
| `INVALID_NIK` | NIK not 16 digits or fails checksum | Verify NIK format and validate with Dukcapil |
| `MISSING_IHS` | Patient/Practitioner missing IHS number | Register entity with SATU SEHAT first |
| `INVALID_ICD10` | ICD-10 code not found | Use valid 2024 ICD-10-CM code |
| `FUTURE_DATE` | Encounter date in future | Check timezone handling (+07:00) |
| `INVALID_REF` | Reference to non-existent resource | Ensure referenced resources are in bundle |

## Bundle Structure

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "fullUrl": "urn:uuid:{uuid}",
      "resource": { /* FHIR Resource */ },
      "request": {
        "method": "POST",
        "url": "{ResourceType}"
      }
    }
  ]
}
```

## Validation Checklist

- [ ] All resources have valid UUIDs
- [ ] Patient has NIK identifier
- [ ] All references resolve within bundle
- [ ] Dates are in ISO 8601 with timezone
- [ ] ICD-10 codes are valid and current
- [ ] Organization ID matches SATU SEHAT registration
- [ ] Bundle size < 50 entries (API limit)
