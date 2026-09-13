/** Matches backend validate_password_policy (non-empty, max 128). */

export const MAX_PASSWORD_LENGTH = 128;

export function validatePasswordPolicy(password: string): string | null {
  if (password.length > MAX_PASSWORD_LENGTH) {
    return `Lösenordet får vara högst ${MAX_PASSWORD_LENGTH} tecken.`;
  }
  if (!password.trim()) return "Lösenordet får inte vara tomt.";
  return null;
}

export function passwordPolicyChecks(password: string, confirm?: string) {
  return {
    nonEmpty: password.trim().length > 0,
    maxLength: password.length <= MAX_PASSWORD_LENGTH,
    match: confirm === undefined || (confirm.length > 0 && password === confirm),
  };
}
