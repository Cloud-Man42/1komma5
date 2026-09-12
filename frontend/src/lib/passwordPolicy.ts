/** Matches backend validate_password_policy (min 10, max 128). */

export const MIN_PASSWORD_LENGTH = 10;
export const MAX_PASSWORD_LENGTH = 128;

export function validatePasswordPolicy(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Lösenordet måste vara minst ${MIN_PASSWORD_LENGTH} tecken.`;
  }
  if (password.length > MAX_PASSWORD_LENGTH) {
    return `Lösenordet får vara högst ${MAX_PASSWORD_LENGTH} tecken.`;
  }
  if (!password.trim()) return "Lösenordet får inte vara tomt.";
  return null;
}

export function passwordPolicyChecks(password: string, confirm?: string) {
  return {
    minLength: password.length >= MIN_PASSWORD_LENGTH,
    maxLength: password.length <= MAX_PASSWORD_LENGTH,
    match: confirm === undefined || (confirm.length > 0 && password === confirm),
  };
}
