import LegalPage from "../legal-page";

export default function PrivacyPage() {
  return (
    <LegalPage
      eyebrow="Privacy and Data Protection"
      title="How VoxaRisk handles personal data and contract review information."
      intro="This Privacy and Data Protection Notice explains the categories of data VoxaRisk may process, the purposes of processing, retention approach, sharing, security, user rights, and service boundaries."
      sections={[
        {
          title: "1. Controller and contact details",
          body: [
            "The controller or responsible business entity for VoxaRisk must be inserted before commercial launch, including legal name, registered address, company number where applicable, and privacy contact email.",
            "For privacy enquiries, data subject requests, or complaints, users should be able to contact VoxaRisk through a dedicated privacy or support channel once the live support address is confirmed."
          ]
        },
        {
          title: "2. Personal data we may collect",
          body: [
            "Depending on how the service is used, VoxaRisk may process account details, contact details, organisation details, billing and subscription metadata, authentication logs, usage records, support communications, scan metadata, uploaded or pasted contract text, extracted text, technical logs, device and browser information, and security/audit records.",
            "Users should avoid uploading unnecessary personal data, special category data, employee records, patient records, payment card data, credentials, or information they are not authorised to submit."
          ]
        },
        {
          title: "3. Purposes of processing",
          body: [
            "VoxaRisk may process data to provide the service, authenticate users, analyse submitted contract material, generate risk outputs, maintain audit and usage records, administer subscriptions, provide support, prevent fraud or misuse, secure the platform, improve reliability, comply with legal obligations, and enforce service terms.",
            "Where contract text is submitted, it is processed for the purpose of extraction, scoring, analysis, reporting, troubleshooting, abuse prevention, and service operation, subject to the selected plan and final retention settings."
          ]
        },
        {
          title: "4. Lawful basis",
          body: [
            "Depending on the context, processing may be based on contract necessity, legitimate interests, legal obligation, consent, or another lawful basis available under applicable data protection law.",
            "Legitimate interests may include operating a secure SaaS platform, preventing abuse, maintaining audit integrity, improving service quality, responding to support requests, and protecting VoxaRisk, users, and third parties."
          ]
        },
        {
          title: "5. Sharing and processors",
          body: [
            "VoxaRisk may use carefully selected service providers for hosting, storage, authentication, analytics, email, billing, monitoring, support, security, and infrastructure operations. These providers may process data only as necessary to provide their services to VoxaRisk.",
            "We do not sell user contract content. We do not share personal data for third-party marketing unless this is expressly introduced, disclosed, and lawfully permitted."
          ]
        },
        {
          title: "6. International transfers",
          body: [
            "Some service providers may process data outside the United Kingdom or the user’s country. Where international transfers occur, VoxaRisk should use appropriate safeguards required by applicable law, such as adequacy arrangements, approved contractual clauses, or equivalent transfer mechanisms.",
            "The final production privacy notice should list material processors and transfer locations once the live supplier stack is finalised."
          ]
        },
        {
          title: "7. Retention",
          body: [
            "VoxaRisk should retain personal data and submitted contract materials only for as long as necessary for service delivery, account administration, security, audit, dispute handling, legal compliance, and legitimate business purposes.",
            "Retention periods may differ for account data, billing records, scan history, report outputs, audit logs, support tickets, and deleted-account records. Final retention durations should be inserted once the production storage policy is fixed."
          ]
        },
        {
          title: "8. User rights",
          body: [
            "Depending on applicable law and circumstances, users may have rights to access, rectification, erasure, restriction, objection, portability, withdrawal of consent, and complaint to a supervisory authority.",
            "Requests may be subject to identity verification, legal exemptions, contractual constraints, security considerations, and the rights of other individuals."
          ]
        },
        {
          title: "9. Security",
          body: [
            "VoxaRisk should apply proportionate technical and organisational measures including access control, authentication, environment separation, audit logging, secure deployment practices, encryption where appropriate, monitoring, and abuse prevention.",
            "No internet service is risk-free. Users remain responsible for controlling what they upload, managing access rights, and ensuring that their organisation has authority to use the service for submitted materials."
          ]
        }
      ]}
    />
  );
}
