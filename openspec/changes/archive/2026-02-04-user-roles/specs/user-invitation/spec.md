## MODIFIED Requirements

### Requirement: Admin can create user invitation
The system SHALL allow users with `users.write` permission to create invitations for new users. The invitation SHALL include the invitee's email address, one or more roles to assign, and a generated unique invite token.

#### Scenario: Create invitation with role selection
- **WHEN** admin enters an email address, selects one or more roles, and clicks "Create Invitation"
- **THEN** system creates an invitation record with the selected roles, a unique token, and an expiry date

#### Scenario: Default role on invitation
- **WHEN** admin creates an invitation without explicitly selecting roles
- **THEN** the system assigns the Manager role by default

#### Scenario: Prevent duplicate pending invitations
- **WHEN** admin tries to invite an email that already has a pending invitation
- **THEN** system SHALL display an error indicating an invitation already exists

#### Scenario: Prevent inviting existing users
- **WHEN** admin tries to invite an email that belongs to an existing user in the tenant
- **THEN** system SHALL display an error indicating the user already exists

### Requirement: Invited user receives assigned roles on account creation
When an invited user completes account setup, the system SHALL assign them the roles specified in the invitation.

#### Scenario: Complete account setup with roles
- **WHEN** invited user sets a valid password and submits the form
- **THEN** system creates the user account with the roles from the invitation, marks invitation as used, and logs the user in
