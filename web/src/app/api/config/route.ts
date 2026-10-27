import { enabledSocial } from "@/server/auth";
import { brokerConfigured } from "@/server/aws";
import { json } from "@/server/http";

export async function GET(request: Request) {
  void request.headers; // runtime data: evaluated per request, never prerendered
  return json({ social: enabledSocial(), awsConnect: brokerConfigured() });
}
