import LegalPage from "../legal-page";

export default function CookiesPage() {
  return (
    <LegalPage
      eyebrow="Cookie Policy"
      title="How VoxaRisk may use cookies and similar technologies."
      intro="This Cookie Policy explains the types of cookies and similar technologies VoxaRisk may use, why they may be used, and how users can manage them."
      sections={[
        {
          title: "1. What cookies are",
          body: [
            "Cookies are small files or similar technologies that can store or access information on a user’s device. They may be used for essential site operation, security, preferences, analytics, performance, support, or marketing.",
            "This policy also covers similar technologies such as local storage, pixels, tags, device identifiers, and comparable browser-based storage or tracking tools."
          ]
        },
        {
          title: "2. Strictly necessary cookies",
          body: [
            "Strictly necessary cookies may be used to operate the website, maintain security, remember session state, route requests, protect forms, support authentication, and provide core functionality.",
            "These cookies are generally required for the service to function and may not require consent where they are genuinely necessary."
          ]
        },
        {
          title: "3. Analytics and performance cookies",
          body: [
            "VoxaRisk may use analytics or performance tools to understand traffic, page performance, service reliability, conversion flows, and product usage. These tools should be configured in a privacy-conscious way wherever possible.",
            "Where consent is required for non-essential analytics or tracking, VoxaRisk should request consent before using those technologies."
          ]
        },
        {
          title: "4. Marketing and third-party cookies",
          body: [
            "If marketing, advertising, retargeting, embedded media, or third-party tracking tools are introduced, they should be clearly disclosed and controlled through an appropriate consent mechanism.",
            "VoxaRisk should not quietly introduce non-essential tracking that conflicts with its trust-first commercial positioning."
          ]
        },
        {
          title: "5. Managing cookies",
          body: [
            "Users can usually control cookies through browser settings. Blocking some cookies may affect the operation, security, performance, or usability of the website and dashboard.",
            "Where non-essential cookies require consent, VoxaRisk will use an appropriate consent mechanism before those technologies are enabled."
          ]
        },
        {
          title: "6. Changes to this policy",
          body: [
            "This policy should be updated when VoxaRisk changes its analytics, hosting, support, advertising, authentication, or tracking tools.",
            "Where specific non-essential cookies are used, VoxaRisk will provide appropriate information about their provider, purpose, duration, and whether they are essential or optional."
          ]
        }
      ]}
    />
  );
}
