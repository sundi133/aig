import "./globals.css";
import Link from "next/link";
import { ReactNode } from "react";

export const metadata = {
  title: "Agentic AI Identity Gateway",
  description: "Identity, authorization, approval, and audit for AI agents.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="layout">
          <aside className="sidebar">
            <h1>
              AIG
              <small>Agentic AI Identity Gateway</small>
            </h1>
            <nav className="nav">
              <Link href="/">Overview</Link>
              <Link href="/agents">Agents</Link>
              <Link href="/tools">Tools</Link>
              <Link href="/runs">Agent runs</Link>
              <Link href="/approvals">Approvals</Link>
              <Link href="/audit">Audit log</Link>
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
