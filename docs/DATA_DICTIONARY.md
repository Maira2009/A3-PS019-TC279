# DATAQUEST Data Dictionary

## Synthetic source fields

### admissions.csv

| Field | Intended label | Notes |
| --- | --- | --- |
| `guardian_phone` | PHONE | Shares a synthetic value with events and support |
| `student_email` | EMAIL | Uses the reserved `example.com` domain |
| `student_name` | PERSON_NAME | Fictional demo names |
| `home_address`, `postal_code` | ADDRESS | Fictional addresses and postal-like values |
| `student_id` | PERSONAL_ID | Synthetic prefixed identifier |
| `phone_model`, `fee_amount` | NONE | Negative controls |

### events.csv

| Field | Intended label | Notes |
| --- | --- | --- |
| `Phone Data Detected` | PHONE | Exact presentation alias |
| `email_address` | EMAIL | Reserved example domain |
| `attendee_name` | PERSON_NAME | Fictional demo names |
| `email_template_name`, `ticket_count` | NONE | Negative controls |

### support.db tickets

| Field | Intended label | Notes |
| --- | --- | --- |
| `mobile` | PHONE | Read from SQLite in read-only mode |
| `contact_email` | EMAIL | Reserved example domain |
| `customer_name` | PERSON_NAME | Fictional demo names |
| `address` | ADDRESS | Fictional demo address |
| `customer_id` | PERSONAL_ID | Synthetic identifier |
| `retry_count`, `transaction_amount` | NONE | Negative controls |

## Metadata import headers

`source_name,object_name,field_name,class_key,purpose_text,retention_duration,retention_basis,last_reviewed_at,owner_label,evidence_reference`

Blank scope columns broaden a declaration. Matching precedence is exact field, source/field or object, class-wide, then workspace-wide.

## Result statuses

- Purpose/retention: `present`, `missing`, `partial`, `unknown`.
- Review: `needs_review`, `accepted`, `rejected`, `review_later`.
- Scan: `queued`, `running`, `completed`, `partial`, `failed`.
- Source: `ready`, `warning`, `failed`.

## Evaluation unit

The unit is one exact `source_name + object_name + field_name + class_key` combination. A wrong-class prediction creates a false positive for the predicted class and a false negative for the expected class. Gold negatives remain in the denominator even when no finding exists.

