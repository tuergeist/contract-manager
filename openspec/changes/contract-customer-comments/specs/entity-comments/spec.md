## ADDED Requirements

### Requirement: Users can add comments to contracts and customers
The system SHALL allow authenticated users to add text comments to contracts and customers. Each comment SHALL record the author, text content, and creation timestamp. Comments SHALL support markdown formatting in the text field.

#### Scenario: Add a comment to a contract
- **WHEN** a user submits a comment with text on a contract detail page
- **THEN** the system creates a `ContractComment` linked to that contract with the current user as author and the current timestamp

#### Scenario: Add a comment to a customer
- **WHEN** a user submits a comment with text on a customer detail page
- **THEN** the system creates a `CustomerNote` linked to that customer with the current user as author and the current timestamp

#### Scenario: Empty comment rejected
- **WHEN** a user submits a comment with blank or whitespace-only text
- **THEN** the system SHALL reject the comment and return a validation error

### Requirement: Users can edit their own most recent comment within 24 hours
The system SHALL allow users to edit only their own most recent comment on a given entity, and only if the comment was created less than 24 hours ago. The backend SHALL enforce both conditions (authorship + recency + most-recent).

#### Scenario: Edit own last comment within 24 hours
- **WHEN** a user edits their most recent comment on an entity and the comment was created less than 24 hours ago
- **THEN** the system updates the comment text and `updated_at` timestamp

#### Scenario: Edit rejected — not the most recent comment
- **WHEN** a user attempts to edit a comment that is not their most recent comment on the entity
- **THEN** the system SHALL reject the edit and return an error

#### Scenario: Edit rejected — older than 24 hours
- **WHEN** a user attempts to edit their most recent comment but it was created more than 24 hours ago
- **THEN** the system SHALL reject the edit and return an error

#### Scenario: Edit rejected — not the author
- **WHEN** a user attempts to edit a comment authored by a different user
- **THEN** the system SHALL reject the edit and return an error

### Requirement: Users can delete their own comments
The system SHALL allow users to delete their own comments at any time, regardless of when the comment was created. Users SHALL NOT be able to delete comments authored by other users.

#### Scenario: Delete own comment
- **WHEN** a user deletes a comment they authored
- **THEN** the system removes the comment from the database

#### Scenario: Delete rejected — not the author
- **WHEN** a user attempts to delete a comment authored by a different user
- **THEN** the system SHALL reject the deletion and return an error

### Requirement: Comment list shows 3 most recent with expand option
The detail pages SHALL display the 3 most recent comments (newest first) in a compact preview. If more than 3 comments exist, a "Show all" button SHALL open a modal displaying the full chronological list.

#### Scenario: Fewer than 4 comments
- **WHEN** an entity has 3 or fewer comments
- **THEN** the UI displays all comments inline and no "Show all" button is shown

#### Scenario: More than 3 comments
- **WHEN** an entity has more than 3 comments
- **THEN** the UI displays the 3 most recent comments inline and shows a "Show all" button

#### Scenario: Show all modal
- **WHEN** a user clicks the "Show all" button
- **THEN** a modal opens displaying all comments for the entity, newest first, with the same comment rendering (markdown, author, timestamp, edit/delete actions)

### Requirement: Comment text renders as markdown
Comment text SHALL be rendered as markdown in the UI. The rendering SHALL support bold, italic, links, lists, inline code, and code blocks. The input SHALL remain a plain textarea (not a rich text editor).

#### Scenario: Markdown rendered on display
- **WHEN** a comment contains markdown syntax (e.g., `**bold**`, `- list item`, `` `code` ``)
- **THEN** the rendered comment displays formatted HTML (bold text, bullet list, inline code)

#### Scenario: Plain text displays correctly
- **WHEN** a comment contains plain text with no markdown syntax
- **THEN** the comment displays as plain text paragraphs

### Requirement: Comments section shares layout with internal notes on contracts
On the contract detail page, the comments section SHALL appear alongside the existing internal notes section. On wider screens, notes and comments SHALL display side by side (two-column grid). On narrow screens, they SHALL stack vertically.

#### Scenario: Contract detail wide screen
- **WHEN** a user views a contract detail page on a wide screen
- **THEN** internal notes appear on the left and comments appear on the right in a two-column layout

#### Scenario: Contract detail narrow screen
- **WHEN** a user views a contract detail page on a narrow screen
- **THEN** internal notes and comments stack vertically

#### Scenario: Customer detail page
- **WHEN** a user views a customer detail page
- **THEN** a comments section is displayed in a similar card layout

### Requirement: GraphQL API exposes comment operations with computed permissions
The GraphQL API SHALL expose queries and mutations for both contract and customer comments. Each comment type SHALL include computed `canEdit` and `canDelete` boolean fields so the frontend does not duplicate permission logic.

#### Scenario: Query contract comments
- **WHEN** a client queries `contractComments(contractId)`
- **THEN** the API returns all comments for that contract, newest first, each with `id`, `text`, `author`, `createdAt`, `updatedAt`, `canEdit`, `canDelete`

#### Scenario: Query customer comments
- **WHEN** a client queries `customerComments(customerId)`
- **THEN** the API returns all comments for that customer, newest first, with the same fields

#### Scenario: canEdit is true only for editable comments
- **WHEN** a comment is the user's most recent comment on the entity AND was created less than 24 hours ago
- **THEN** `canEdit` SHALL be `true`; otherwise `false`

#### Scenario: canDelete is true only for own comments
- **WHEN** the current user is the comment author
- **THEN** `canDelete` SHALL be `true`; otherwise `false`

### Requirement: Add comment via modal with textarea
The UI SHALL provide an "Add comment" button that opens a modal dialog containing a textarea and a save button. The modal SHALL close after successful submission and the comment list SHALL update immediately.

#### Scenario: Add comment flow
- **WHEN** a user clicks "Add comment", types text in the textarea, and clicks save
- **THEN** the modal closes, the new comment appears at the top of the comment list, and no page reload is required

#### Scenario: Cancel adding comment
- **WHEN** a user opens the add comment modal and clicks cancel or closes the modal
- **THEN** no comment is created and the modal closes
