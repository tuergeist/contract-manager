import { useTranslation } from 'react-i18next'
import { ProfileEdit } from './ProfileEdit'
import { PasswordChange } from './PasswordChange'

export function UserSettings() {
  const { t, i18n } = useTranslation()

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang)
  }

  return (
    <div className="space-y-6">
      {/* Profile Edit */}
      <ProfileEdit />

      {/* Password Change */}
      <PasswordChange />

      {/* Language */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="text-lg font-medium">{t('settings.language')}</h2>
        <p className="mt-1 text-sm text-gray-500">{t('settings.languageDescription')}</p>

        <div className="mt-4 flex gap-2">
          <button
            onClick={() => changeLanguage('de')}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              i18n.language === 'de'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Deutsch
          </button>
          <button
            onClick={() => changeLanguage('en')}
            className={`rounded-md px-4 py-2 text-sm font-medium ${
              i18n.language === 'en'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            English
          </button>
        </div>
      </div>
    </div>
  )
}
