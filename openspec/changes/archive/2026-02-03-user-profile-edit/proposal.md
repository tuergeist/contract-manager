# User Profile Edit

## Problem
Users currently cannot update their own profile information (name and email). This data can only be changed directly in the database.

## Proposed Solution
Allow authenticated users to edit their own profile information:
- First name
- Last name
- Email address

Changes apply to the user's own account only. Email changes should validate the new email is not already in use by another user in the same tenant.

## Scope
- Add GraphQL mutation `updateProfile` for users to update their own data
- Add profile editing UI in Settings page
- Validate email uniqueness within tenant

## Out of Scope
- Admin editing other users' profiles
- Avatar/profile picture
- Changing username (email is the identifier)
