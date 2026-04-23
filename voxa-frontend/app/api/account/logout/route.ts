import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "voxarisk_account_session";

export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
  return NextResponse.json({ status: "signed_out" });
}
