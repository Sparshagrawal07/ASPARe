import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { AssumeRoleCommand, STSClient } from "@aws-sdk/client-sts";
import { NodeHttpHandler } from "@smithy/node-http-handler";
import { awsCredentialsProvider } from "@vercel/oidc-aws-credentials-provider";
import { HttpsProxyAgent } from "https-proxy-agent";

export type TempCredentials = { accessKeyId: string; secretAccessKey: string; sessionToken: string };

/** ASPARe's own AWS identity: Vercel OIDC in production (no stored secrets), the local AWS profile in development. */
function brokerCredentials() {
  if (process.env.VERCEL && process.env.AWS_ROLE_ARN) return awsCredentialsProvider({ roleArn: process.env.AWS_ROLE_ARN });
  return undefined; // default credential chain
}

const BROKER_REGION = process.env.ASPARE_AWS_REGION ?? "ap-southeast-2";

/** Honour an egress proxy when the environment has one (some dev networks). Absent on Vercel, so a no-op there. */
function proxyHandler() {
  const proxy = process.env.HTTPS_PROXY ?? process.env.https_proxy;
  if (!proxy) return undefined;
  return new NodeHttpHandler({ httpsAgent: new HttpsProxyAgent(proxy) });
}

export function brokerConfigured(): boolean {
  return Boolean(process.env.TRUST_ACCOUNT_ID && process.env.TEMPLATE_BUCKET);
}

export function trustAccountId(): string {
  return process.env.TRUST_ACCOUNT_ID ?? "";
}

export function roleArn(accountId: string, roleName: string): string {
  return `arn:aws:iam::${accountId}:role/${roleName}`;
}

export class AssumeError extends Error {}

/** Assume a customer role (read or fix) with the connection's external id. Returns one-hour credentials. */
export async function assume(opts: { accountId: string; roleName: string; externalId: string; sessionTag: string }): Promise<TempCredentials> {
  const sts = new STSClient({ region: BROKER_REGION, credentials: brokerCredentials(), requestHandler: proxyHandler() });
  try {
    const out = await sts.send(
      new AssumeRoleCommand({
        RoleArn: roleArn(opts.accountId, opts.roleName),
        RoleSessionName: `aspare-${opts.sessionTag}`.slice(0, 64),
        ExternalId: opts.externalId,
        DurationSeconds: 3600,
      }),
    );
    const c = out.Credentials;
    if (!c?.AccessKeyId || !c.SecretAccessKey || !c.SessionToken) throw new AssumeError("AWS returned no credentials");
    return { accessKeyId: c.AccessKeyId, secretAccessKey: c.SecretAccessKey, sessionToken: c.SessionToken };
  } catch (err) {
    const name = (err as { name?: string }).name ?? "Error";
    console.error("assume-role failed:", name, (err as Error).message); // server log only
    if (name === "AccessDenied" || name === "AccessDeniedException")
      throw new AssumeError("AWS refused the role. Check that the stack finished creating and that the account id is right.");
    throw new AssumeError(`Could not reach AWS (${name}).`);
  }
}

/** A short-lived link to a CloudFormation template that lives in a private bucket. */
export async function presignedTemplateUrl(templateKey: string): Promise<string> {
  const s3 = new S3Client({ region: BROKER_REGION, credentials: brokerCredentials(), requestHandler: proxyHandler() });
  return getSignedUrl(s3, new GetObjectCommand({ Bucket: process.env.TEMPLATE_BUCKET!, Key: templateKey }), { expiresIn: 3000 });
}

export function quickCreateUrl(opts: { region: string; stackName: string; templateUrl: string; params: Record<string, string> }): string {
  const q = [
    `templateURL=${encodeURIComponent(opts.templateUrl)}`,
    `stackName=${encodeURIComponent(opts.stackName)}`,
    ...Object.entries(opts.params).map(([k, v]) => `param_${k}=${encodeURIComponent(v)}`),
  ].join("&");
  return `https://console.aws.amazon.com/cloudformation/home?region=${opts.region}#/stacks/quickcreate?${q}`;
}
