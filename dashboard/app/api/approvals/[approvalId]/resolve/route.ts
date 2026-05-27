import { NextRequest, NextResponse } from "next/server";

import { api } from "@/lib/api";

export async function POST(req: NextRequest, { params }: { params: { approvalId: string } }) {
  const body = await req.json();
  try {
    const data = await api(`/v1/approvals/${encodeURIComponent(params.approvalId)}/resolve`, {
      method: "POST",
      body,
    });
    return NextResponse.json(data);
  } catch (e) {
    return new NextResponse((e as Error).message, { status: 500 });
  }
}
