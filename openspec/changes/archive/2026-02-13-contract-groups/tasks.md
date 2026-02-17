## 1. Backend Model

- [x] 1.1 Create ContractGroup model in `apps/contracts/models.py` (tenant, customer FK, name, timestamps)
- [x] 1.2 Add unique constraint on (customer, name)
- [x] 1.3 Add nullable group ForeignKey to Contract model with on_delete=SET_NULL
- [x] 1.4 Create and run migrations

## 2. Backend GraphQL Types

- [x] 2.1 Create ContractGroupType in `apps/contracts/schema.py`
- [x] 2.2 Add contract_count field to ContractGroupType
- [x] 2.3 Add group field to ContractType (returns ContractGroupType or null)

## 3. Backend GraphQL Queries

- [x] 3.1 Add contractGroups(customerId) query returning groups for a customer

## 4. Backend GraphQL Mutations

- [x] 4.1 Add createContractGroup(customerId, name) mutation with contracts.write permission
- [x] 4.2 Add updateContractGroup(groupId, name) mutation with contracts.write permission
- [x] 4.3 Add deleteContractGroup(groupId) mutation with contracts.write permission
- [x] 4.4 Add assignContractToGroup(contractId, groupId) mutation with contracts.write permission
- [x] 4.5 Add validation: group and contract must belong to same customer

## 5. Frontend - Contract Edit Page

- [x] 5.1 Add GraphQL query to fetch contract groups for customer
- [x] 5.2 Add group selector dropdown to ContractForm overview section
- [x] 5.3 Include groupId in contract update mutation
- [x] 5.4 Handle "create new group" option in dropdown

## 6. Frontend - Customer Detail Contracts Table

- [x] 6.1 Add group column to contracts table in CustomerDetail.tsx
- [x] 6.2 Display group name or "-" for ungrouped contracts
- [x] 6.3 Add inline group edit popover/dropdown
- [x] 6.4 Add "create new group" option in inline editor
- [x] 6.5 Call assignContractToGroup mutation on selection

## 7. Translations

- [x] 7.1 Add English translations for group-related UI strings
- [x] 7.2 Add German translations for group-related UI strings

## 8. Testing

- [x] 8.1 Test group CRUD mutations (backend tests pass)
- [x] 8.2 Test cross-customer assignment prevention (backend logic)
- [x] 8.3 Test group deletion sets contract.group to null (on_delete=SET_NULL)
- [x] 8.4 Verify TypeScript compiles without errors
