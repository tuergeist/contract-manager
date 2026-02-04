## ADDED Requirements

### Requirement: User can update their own profile
Authenticated users SHALL be able to update their own first name, last name, and email address.

#### Scenario: Update name successfully
- **WHEN** user enters new first name and/or last name and saves
- **THEN** system updates the user record and shows success message

#### Scenario: Update email successfully
- **WHEN** user enters a new email that is not in use and saves
- **THEN** system updates the user's email and shows success message

#### Scenario: Email already in use
- **WHEN** user enters an email that belongs to another user in the tenant
- **THEN** system displays an error that the email is already in use

#### Scenario: Invalid email format
- **WHEN** user enters an invalid email format
- **THEN** system displays a validation error
