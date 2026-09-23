import LegalPage, { legalStyles as s } from './LegalPage';

export default function AGB() {
  return (
    <LegalPage title="Allgemeine Geschäftsbedingungen" updatedAt="23.09.2026">
      <div>
        <h2 style={s.h2}>1. Geltungsbereich</h2>
        <p>
          Diese Bedingungen gelten für die Nutzung von OnboardGuide AI (onboardguide.leadspeak.de), einer
          KI-gestützten Onboarding-Plattform für Unternehmen, angeboten von Mahmood AL-Djabboori (siehe{' '}
          <a href="/impressum" style={s.a}>Impressum</a>). Kunde ist stets das sich registrierende
          Unternehmen, nicht die einzelnen Mitarbeitenden.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>2. Vertragsschluss</h2>
        <p>
          Mit der Registrierung einer Firma über <a href="/signup" style={s.a}>/signup</a> kommt ein
          Nutzungsvertrag zu den jeweils zum Zeitpunkt der Registrierung gültigen Bedingungen zustande. Der
          Zugang startet im nicht freigeschalteten Testzustand; produktive Nutzung erfordert eine
          Freischaltung durch den Anbieter gemäß Ziffer 4.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>3. Leistungsbeschreibung</h2>
        <p>
          OnboardGuide AI stellt eine mandantenfähige Plattform zur Mitarbeiter-Einarbeitung bereit:
          Dokumentenverwaltung mit KI-gestützter Suche, einen Chat-Assistenten, Aufgabenverwaltung sowie
          Abwesenheitsverwaltung. Der Funktionsumfang kann sich abhängig vom gewählten Plan unterscheiden.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>4. Preise, Nutzungsmodell und Zahlung</h2>
        <p>
          Es findet aktuell kein automatisierter Zahlungsvorgang innerhalb der Anwendung statt. Nach der
          Registrierung kann über die Kontakt-/Abo-Funktion in der Anwendung eine Freischaltung angefragt
          werden; der Anbieter meldet sich daraufhin manuell mit den individuellen Konditionen (z.B. Rechnung
          oder Lastschrift), bevor ein kostenpflichtiges Nutzungsverhältnis zustande kommt. [TODO: konkrete
          Preise/Zahlungsmodalitäten ergänzen, sobald ein Plan-Modell final feststeht.]
        </p>
      </div>

      <div>
        <h2 style={s.h2}>5. Laufzeit und Kündigung</h2>
        <p>
          Sofern nichts anderes vereinbart wurde, läuft das Nutzungsverhältnis auf unbestimmte Zeit. Der
          Kunde kann jederzeit die Löschung seines Firmenkontos beim Anbieter beantragen. [TODO:
          Kündigungsfristen/-bedingungen ergänzen, sobald final.]
        </p>
      </div>

      <div>
        <h2 style={s.h2}>6. Nutzungsvoraussetzungen und Pflichten des Kunden</h2>
        <p>
          Der Kunde ist für die Richtigkeit seiner Kontoangaben sowie für die Rechtmäßigkeit der von ihm
          hochgeladenen Dokumente und der Nutzerkonten seiner Mitarbeitenden verantwortlich, insbesondere für
          die Einholung erforderlicher Einwilligungen gegenüber diesen. Automatisierte Massenzugriffe und die
          Verletzung von Rechten Dritter sind untersagt.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>7. Haftung</h2>
        <p>
          Die KI-gestützten Antworten des Chat-Assistenten liefern Unterstützung bei der Einarbeitung, jedoch
          keine verbindliche Auskunft. Eine Haftung für die inhaltliche Richtigkeit automatisiert erzeugter
          Antworten ist ausgeschlossen, soweit gesetzlich zulässig. Im Übrigen haftet der Anbieter nur bei
          Vorsatz und grober Fahrlässigkeit sowie nach den gesetzlichen Vorgaben bei Verletzung wesentlicher
          Vertragspflichten.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>8. Änderungen dieser Bedingungen</h2>
        <p>
          Änderungen dieser Bedingungen werden dem Kunden in geeigneter Form (z.B. Hinweis in der Anwendung
          oder per E-Mail) mitgeteilt.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>9. Schlussbestimmungen</h2>
        <p>
          Es gilt das Recht der Bundesrepublik Deutschland. Sollten einzelne Bestimmungen unwirksam sein,
          bleibt die Wirksamkeit der übrigen Bestimmungen unberührt.
        </p>
      </div>
    </LegalPage>
  );
}
