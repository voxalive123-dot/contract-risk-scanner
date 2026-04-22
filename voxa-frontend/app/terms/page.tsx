import LegalPage from "../legal-page";

export default function TermsPage() {
  return (
    <LegalPage
      eyebrow="Terms and Conditions"
      title="Terms governing access to and use of VoxaRisk."
      intro="These Terms set the commercial and operational rules for using VoxaRisk, including the platform boundary, permitted use, account responsibilities, payment terms, intellectual property, liability limits, and dispute framework."
      sections={[
        {
          title: "1. Introduction",
          body: [
            "These Terms and Conditions apply to access to and use of VoxaRisk, including the website, dashboard, contract review tools, reports, outputs, interfaces, and related services. By accessing or using VoxaRisk, you agree to be bound by these Terms.",
            "References to “VoxaRisk”, “we”, “us”, or “our” mean the operator of the VoxaRisk service, including its website, dashboard, contract risk intelligence tools, reports, and related services."
          ]
        },
        {
          title: "2. Nature of the service",
          body: [
            "VoxaRisk provides automated contract risk intelligence and decision-support observations. It is designed to help users identify risk-bearing contract patterns, prioritise review, inspect evidence, and structure commercial escalation.",
            "VoxaRisk does not provide legal advice, legal opinions, contract approval, regulatory advice, professional legal services, or a substitute for qualified legal review. Users remain responsible for all commercial, legal, operational, and approval decisions."
          ]
        },
        {
          title: "3. User responsibilities",
          body: [
            "You must use VoxaRisk lawfully, responsibly, and only for legitimate contract review and business decision-support purposes. You are responsible for the accuracy, lawfulness, and suitability of any content you upload, paste, scan, or submit.",
            "You must not upload unlawful material, confidential information you are not authorised to process, personal data without a lawful basis, malicious code, credentials, payment card data, or material that infringes third-party rights."
          ]
        },
        {
          title: "4. Accounts, access, and security",
          body: [
            "Where account access, API keys, subscription credentials, or organisation-level access controls are provided, you are responsible for maintaining their confidentiality and for all activity conducted through your account or credentials.",
            "We may suspend, restrict, or terminate access where we reasonably suspect misuse, unauthorised access, security risk, breach of these Terms, non-payment, abuse of the service, or activity that may harm VoxaRisk, users, third parties, or system integrity."
          ]
        },
        {
          title: "5. Outputs and reliance",
          body: [
            "VoxaRisk outputs are generated from automated rules, heuristics, extraction logic, and system analysis. Outputs may be incomplete, inaccurate, context-limited, or unsuitable for a particular transaction, jurisdiction, sector, contract type, or legal question.",
            "You must review outputs critically, inspect the clause evidence, consider missing context, and seek professional advice where appropriate. You must not treat VoxaRisk output as final legal clearance or as a guarantee of contract safety."
          ]
        },
        {
          title: "6. Plans, billing, currency, cancellation, and refunds",
          body: [
            "VoxaRisk may offer free, paid, subscription, usage-based, promotional, trial, business, executive, or enterprise plans. Plan names, usage allowances, scan limits, rate limits, report limits, storage limits, features, renewal periods, and access rights may vary by plan and may be changed with notice where required by law or contract.",
            "Unless stated otherwise at checkout, VoxaRisk plan pricing is set by reference to the published base price for the relevant plan. Where payment is offered in pounds sterling, US dollars, euros, or another supported currency, the amount shown at checkout is the applicable native-currency amount for that transaction. Currency conversion, card issuer charges, bank fees, foreign exchange fees, taxes, and payment processor charges may be outside VoxaRisk’s control.",
            "Payments may be processed by third-party payment providers. VoxaRisk does not require users to submit card details directly to VoxaRisk where a hosted payment provider is used. The payment provider’s own terms, authentication requirements, fraud checks, payment method rules, and dispute processes may apply in addition to these Terms.",
            "Paid subscriptions renew automatically unless cancelled before the renewal date through the available cancellation method or billing management process. Cancelling a subscription stops future renewal charges but does not automatically create a refund for the current paid period, unless a refund is required by applicable law, expressly promised at checkout, or agreed by VoxaRisk in writing.",
            "VoxaRisk is a digital service. Once paid access, subscription functionality, scan allowance, report functionality, account access, or other paid service access has started, fees are generally non-refundable to the fullest extent permitted by applicable law. This does not limit any mandatory consumer rights, statutory cancellation rights, rights arising from unauthorised payment, duplicate billing, material service failure, or any refund right that cannot lawfully be excluded.",
            "For business users, fees are non-refundable once the paid service period or paid access has commenced, except where VoxaRisk has charged the user in error, duplicate billing has occurred, the service has materially failed in a way that VoxaRisk accepts requires a refund, or a refund is required by applicable law. For consumer users, any statutory cancellation or refund rights that apply in the user’s jurisdiction are preserved and are not excluded by these Terms.",
            "Users must provide accurate billing information and ensure that they are authorised to use the selected payment method. VoxaRisk may suspend, restrict, downgrade, or terminate paid access for failed payment, chargeback, suspected fraud, payment abuse, breach of these Terms, or misuse of the service.",
            "The service may be unavailable, interrupted, degraded, delayed, or modified from time to time for maintenance, security, hosting, deployment, third-party provider issues, abuse prevention, or operational reasons."
          ]
        },
        {
          title: "7. Intellectual property",
          body: [
            "VoxaRisk, including its software, interface, branding, scoring logic, rule structures, workflows, reports, designs, and documentation, is owned by or licensed to VoxaRisk and is protected by intellectual property laws.",
            "You retain responsibility for and rights in contract text or documents you submit, subject to the licence necessary for us to process that content to provide, secure, operate, maintain, and improve the service."
          ]
        },
        {
          title: "8. Limitation of liability",
          body: [
            "To the fullest extent permitted by law, VoxaRisk is provided on an “as is” and “as available” basis. We do not warrant that the service will identify every risk, produce legally complete analysis, or be suitable for every contract, jurisdiction, user, or commercial decision.",
            "Nothing in these Terms excludes liability that cannot be excluded under applicable law. Subject to that, VoxaRisk shall not be liable for indirect, consequential, special, punitive, loss-of-profit, loss-of-business, loss-of-opportunity, loss-of-data, or decision-related losses arising from use of or reliance on the service."
          ]
        },
        {
          title: "9. Governing law and changes",
          body: [
            "Unless otherwise stated in a signed agreement, these Terms are intended to be governed by the laws of England and Wales, with disputes subject to the courts of England and Wales.",
            "We may update these Terms from time to time. Material changes should be notified through the website, account interface, email, or another reasonable method."
          ]
        }
      ]}
    />
  );
}
