import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LoginForm } from "./LoginForm";
import { ToastProvider } from "@/components/admin-ui";

const replace = vi.fn();
const login = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("next=%2Faccount"),
}));

vi.mock("@/lib/authContext", () => ({
  useAuth: () => ({
    login,
    isAuthenticated: false,
    loading: false,
  }),
}));

function renderLogin() {
  return render(
    <ToastProvider>
      <LoginForm />
    </ToastProvider>,
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    replace.mockReset();
    login.mockReset();
  });

  it("renders login form", () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: /Logga in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/E-post \/ användarnamn/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Lösenord/i)).toBeInTheDocument();
  });

  it("shows generic error on failed login", async () => {
    login.mockRejectedValueOnce(new Error("401"));
    renderLogin();
    fireEvent.change(screen.getByLabelText(/E-post \/ användarnamn/i), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Lösenord/i), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /Logga in/i }));
    expect(await screen.findByText(/Felaktigt användarnamn eller lösenord/i)).toBeInTheDocument();
  });

  it("redirects to next path after successful login", async () => {
    login.mockResolvedValueOnce({});
    renderLogin();
    fireEvent.change(screen.getByLabelText(/E-post \/ användarnamn/i), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Lösenord/i), { target: { value: "AdminPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: /Logga in/i }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/account"));
  });

  it("disables submit while loading", async () => {
    let resolveLogin: () => void = () => undefined;
    login.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve as () => void;
        }),
    );
    renderLogin();
    fireEvent.change(screen.getByLabelText(/E-post \/ användarnamn/i), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Lösenord/i), { target: { value: "AdminPass123!" } });
    fireEvent.click(screen.getByRole("button", { name: /Logga in/i }));
    expect(screen.getByRole("button", { name: /Loggar in/i })).toBeDisabled();
    resolveLogin();
    await waitFor(() => expect(screen.getByRole("button", { name: /Logga in/i })).not.toBeDisabled());
  });
});
