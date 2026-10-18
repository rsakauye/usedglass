// Kit (ConvertKit) signup form used by the footer and /newsletter/.
// Default: Kit form 10061701 ("Newsletter site") in the UsedGlass Kit account.
// Override at build time with PUBLIC_KIT_FORM_ID (repo variable KIT_FORM_ID). Set it to "off" to hide the form.
const envId = (import.meta.env.PUBLIC_KIT_FORM_ID || '').trim();
export const KIT_FORM_ID = envId === 'off' ? '' : (envId || '10061701');
export const kitAction = KIT_FORM_ID ? `https://app.kit.com/forms/${KIT_FORM_ID}/subscriptions` : '';
