"use client";



import Link from "next/link";

import { useAuth } from "@/lib/authContext";



function userInitials(displayName: string): string {

  const parts = displayName.trim().split(/\s+/).filter(Boolean);

  if (parts.length >= 2) {

    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();

  }

  return displayName.slice(0, 2).toUpperCase();

}



type UserMenuProps = {

  compact?: boolean;

};



export function UserMenu({ compact = false }: UserMenuProps) {

  const { user, logout, can } = useAuth();

  if (!user) return null;



  const menuBody = (

    <>

      <div className="user-menu-meta">

        <span className="user-menu-label">{user.displayName}</span>

        <span className="muted user-menu-roles">{user.roles.join(", ")}</span>

      </div>

      <Link href="/account">Mitt konto</Link>

      {can("users.read") || can("roles.read") || can("audit.read") ? (
        <Link href="/admin/users">Administration</Link>
      ) : null}

      <button type="button" onClick={() => void logout()}>

        Logga ut

      </button>

    </>

  );



  if (compact) {

    return (

      <details className="user-menu user-menu-compact">

        <summary className="idash-user-avatar" aria-label={`Konto: ${user.displayName}`}>

          {userInitials(user.displayName)}

        </summary>

        <div className="user-menu-dropdown">{menuBody}</div>

      </details>

    );

  }



  return <div className="user-menu">{menuBody}</div>;

}


