import LegalPage from "../legal-page";

export default function DisclaimerPage() {
  return (
    <LegalPage
      eyebrow="Decision Boundary"
      title="VoxaRisk is contract risk intelligence, not legal advice."
      intro="This page states the operational boundary of VoxaRisk so users understand what the platform does, what it does not do, and where professional judgement remains required."
      sections={[
        {
          title: "1. No legal advice",
          body: [
            "VoxaRisk does not provide legal advice, legal opinions, legal representation, contract approval, compliance certification, regulatory advice, or professional legal services.",
            "Outputs are automated observations intended to support review discipline, evidence inspection, commercial prioritisation, and escalation decisions. They are not a substitute for qualified legal, commercial, financial, technical, or professional advice."
          ]
        },
        {
          title: "2. Automated analysis limits",
          body: [
            "VoxaRisk may miss risks, misclassify wording, overstate issues, understate issues, fail to recognise context, or produce outputs affected by extraction quality, OCR quality, document formatting, unusual drafting, missing schedules, jurisdictional differences, or incomplete inputs.",
            "Users must inspect the underlying clause evidence and consider the full agreement, negotiation history, commercial context, governing law, sector, transaction value, operational dependencies, and risk appetite."
          ]
        },
        {
          title: "3. No guarantee of outcome",
          body: [
            "VoxaRisk does not guarantee that a contract is safe, enforceable, compliant, commercially acceptable, complete, negotiable, or suitable for signing.",
            "Any decision to accept, reject, negotiate, escalate, sign, perform, terminate, or rely on a contract remains the responsibility of the user and their organisation."
          ]
        },
        {
          title: "4. Professional review",
          body: [
            "Users should obtain professional advice where a contract involves material liability, indemnity, unusual jurisdiction, data processing, regulated activity, employment issues, intellectual property, financing, high transaction value, operational dependency, or strategic exposure.",
            "VoxaRisk is most useful as an early-warning and prioritisation layer, not as the final authority."
          ]
        },
        {
          title: "5. Evidence-first use",
          body: [
            "The correct use of VoxaRisk is to read the decision signal, review the ranked risks, inspect the clause evidence, understand the commercial consequence, and escalate where the consequence warrants.",
            "The incorrect use of VoxaRisk is to treat a score or summary as final approval without human review."
          ]
        }
      ]}
    />
  );
}
