import { gql } from '@apollo/client'

/**
 * Shared GraphQL documents, TypeScript types and helpers for the
 * payment reminders / Mahnungen (dunning) feature.
 */

// --- Types ---

export interface DunningSettings {
  defaultPaymentTermDays: number
  overdueRedThresholdDays: number
  mahnfaehigThresholdDays: number
  interestRate: string
  defaultFeePerStage: Record<string, string>
  templates: DunningTemplates
}

export interface DunningTemplateStage {
  title: string
  subject: string
  body: string
}

export interface DunningTemplates {
  de?: Record<string, DunningTemplateStage>
  en?: Record<string, DunningTemplateStage>
}

export interface PaymentReminder {
  id: number
  invoiceRecordId: number
  invoiceNumber: string
  customerId: number | null
  customerName: string
  stage: number
  language: string
  title: string
  subject: string
  bodyText: string
  feeAmount: string
  interestAmount: string
  interestRateSnapshot: string
  interestDays: number
  pdfUrl: string | null
  sentAt: string | null
  sentTo: string[]
  createdAt: string
}

export interface PaymentReminderDraft {
  invoiceRecordId: number
  invoiceNumber: string
  stage: number
  language: string
  title: string
  subject: string
  bodyText: string
  feeAmount: string
  interestAmount: string
  interestRate: string
  interestDays: number
  overdueDays: number
}

// --- Queries ---

export const DUNNING_SETTINGS_QUERY = gql`
  query DunningSettings {
    dunningSettings {
      defaultPaymentTermDays
      overdueRedThresholdDays
      mahnfaehigThresholdDays
      interestRate
      defaultFeePerStage
      templates
    }
  }
`

// --- Mutations ---

export const CREATE_PAYMENT_REMINDER = gql`
  mutation CreatePaymentReminder($invoiceRecordId: Int!, $stage: Int) {
    createPaymentReminder(invoiceRecordId: $invoiceRecordId, stage: $stage) {
      success
      error
      draft {
        invoiceRecordId
        invoiceNumber
        stage
        language
        title
        subject
        bodyText
        feeAmount
        interestAmount
        interestRate
        interestDays
        overdueDays
      }
    }
  }
`

export const SEND_PAYMENT_REMINDER = gql`
  mutation SendPaymentReminder(
    $invoiceRecordId: Int!
    $stage: Int!
    $language: String!
    $title: String!
    $subject: String!
    $bodyText: String!
    $includeFee: Boolean
    $includeInterest: Boolean
  ) {
    sendPaymentReminder(
      invoiceRecordId: $invoiceRecordId
      stage: $stage
      language: $language
      title: $title
      subject: $subject
      bodyText: $bodyText
      includeFee: $includeFee
      includeInterest: $includeInterest
    ) {
      success
      error
      reminder {
        id
        stage
        sentAt
      }
    }
  }
`

export const SAVE_DUNNING_SETTINGS = gql`
  mutation SaveDunningSettings($input: DunningSettingsInput!) {
    saveDunningSettings(input: $input) {
      success
      error
      settings {
        defaultPaymentTermDays
        overdueRedThresholdDays
        mahnfaehigThresholdDays
        interestRate
        defaultFeePerStage
        templates
      }
    }
  }
`

export const UPDATE_CUSTOMER_PAYMENT_TERM = gql`
  mutation UpdateCustomerPaymentTerm($input: UpdateCustomerPaymentTermInput!) {
    updateCustomerPaymentTerm(input: $input) {
      success
      error
      paymentTermDays
    }
  }
`

// --- Reminder fields fragment (raw selection set string for reuse) ---

export const PAYMENT_REMINDER_FIELDS = `
  id
  invoiceRecordId
  invoiceNumber
  customerId
  customerName
  stage
  language
  title
  subject
  bodyText
  feeAmount
  interestAmount
  interestRateSnapshot
  interestDays
  pdfUrl
  sentAt
  sentTo
  createdAt
`

// --- Helpers ---

/**
 * Translation key for a dunning stage label.
 * stage 0 = payment reminder, 1-3 = 1st/2nd/3rd reminder.
 */
export function stageLabelKey(stage: number): string {
  switch (stage) {
    case 0:
      return 'reminders.stage.0'
    case 1:
      return 'reminders.stage.1'
    case 2:
      return 'reminders.stage.2'
    case 3:
      return 'reminders.stage.3'
    default:
      return 'reminders.stage.0'
  }
}
