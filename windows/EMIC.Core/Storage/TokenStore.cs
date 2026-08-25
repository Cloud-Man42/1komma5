using System.Security.Cryptography;
using System.Text;

namespace EMIC.Core.Storage;

public sealed class TokenStore
{
    private readonly string _tokenPath;

    public TokenStore(string? rootDirectory = null)
    {
        var root = rootDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "EMIC");
        Directory.CreateDirectory(root);
        _tokenPath = Path.Combine(root, "device-token.dat");
    }

    public void SaveToken(string token)
    {
        var plain = Encoding.UTF8.GetBytes(token.Trim());
        var protectedBytes = ProtectedData.Protect(plain, optionalEntropy: null, DataProtectionScope.CurrentUser);
        File.WriteAllBytes(_tokenPath, protectedBytes);
    }

    public string? LoadToken()
    {
        if (!File.Exists(_tokenPath))
        {
            return null;
        }

        try
        {
            var protectedBytes = File.ReadAllBytes(_tokenPath);
            var plain = ProtectedData.Unprotect(protectedBytes, optionalEntropy: null, DataProtectionScope.CurrentUser);
            return Encoding.UTF8.GetString(plain);
        }
        catch (CryptographicException)
        {
            return null;
        }
    }

    public void ClearToken()
    {
        if (File.Exists(_tokenPath))
        {
            File.Delete(_tokenPath);
        }
    }

    public bool HasToken() => !string.IsNullOrWhiteSpace(LoadToken());
}
