import LegalPage, { legalStyles as s } from './LegalPage';

export default function Datenschutz() {
  return (
    <LegalPage title="Datenschutzerklärung" updatedAt="23.09.2026">
      <div>
        <h2 style={s.h2}>1. Verantwortlichkeit</h2>
        <p>
          OnboardGuide AI wird als Software-as-a-Service an Unternehmen ("Kunde") lizenziert. Für die
          personenbezogenen Daten der Mitarbeitenden des Kunden (Konten, Aufgaben, Dokumentenzugriff,
          Chat-Anfragen) ist der Kunde datenschutzrechtlich Verantwortlicher im Sinne der DSGVO. Mahmood
          AL-Djabboori (Kontakt siehe <a href="/impressum" style={s.a}>Impressum</a>) verarbeitet diese Daten
          als Auftragsverarbeiter im Auftrag des Kunden (Art. 28 DSGVO); ein Auftragsverarbeitungsvertrag
          (AVV) wird Geschäftskunden auf Anfrage bereitgestellt. Für die Registrierungsdaten der Firma selbst
          (z.B. Rechnungskontakt) ist Mahmood AL-Djabboori Verantwortlicher.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>2. Welche Daten wir verarbeiten</h2>
        <p>
          Kontodaten (Benutzername, E-Mail, Passwort-Hash, Rolle, Abteilung/Projekt); von der Firma
          hochgeladene Onboarding-Dokumente inkl. daraus extrahiertem Text und Bildern; an den KI-Assistenten
          gestellte Fragen samt Antworten (Chat-Verlauf); Aufgaben und Abwesenheitsanträge, soweit im Rahmen
          der jeweiligen Funktion angelegt.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>3. Zwecke und Rechtsgrundlagen</h2>
        <p>
          Bereitstellung und Betrieb der Onboarding-Plattform im Rahmen des Auftragsverarbeitungsverhältnisses
          mit dem Kundenunternehmen (Art. 6 Abs. 1 lit. b bzw. f DSGVO auf Ebene des Kunden); berechtigtes
          Interesse (Art. 6 Abs. 1 lit. f DSGVO) für Missbrauchs- und Kostenschutz, u.a. Rate-Limiting bei
          Login/Registrierung.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>4. Mandantentrennung</h2>
        <p>
          OnboardGuide AI ist mandantenfähig: Jede Firma (Organization) ist technisch strikt von allen
          anderen getrennt. Nutzer:innen, Dokumente, Chat-Verläufe, Aufgaben und Abwesenheiten einer Firma
          sind für andere Firmen unter keinen Umständen einsehbar.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>5. Eingesetzte Dienstleister (Unterauftragsverarbeitung)</h2>
        <p>
          Für die KI-gestützte Dokumentensuche und Chat-Antworten werden Modelle von OpenAI eingesetzt; für
          die Objekt-Speicherung hochgeladener Dokumente/Bilder ein S3-kompatibler Anbieter (Cloudflare R2);
          für Datenbank, Backend- und Frontend-Hosting die Anbieter Neon, Render und Vercel; für den Versand
          von Transaktions-Mails (z.B. Kontakt-/Abo-Anfragen) der Dienst Resend. Mit allen eingebundenen
          Anbietern, die personenbezogene Daten im Auftrag verarbeiten, besteht bzw. wird ein
          Auftragsverarbeitungsvertrag (Art. 28 DSGVO) geschlossen. Hochgeladene Dokumente und Chat-Inhalte
          werden nicht zum Training von Drittanbieter-Modellen verwendet.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>6. Speicherdauer</h2>
        <p>
          Daten werden für die Dauer des Vertragsverhältnisses zwischen Kunde und Anbieter gespeichert und
          nach dessen Beendigung bzw. auf Anfrage des Kunden gelöscht, soweit keine gesetzlichen
          Aufbewahrungspflichten entgegenstehen.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>7. Deine Rechte</h2>
        <p>
          Betroffene Personen haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16), Löschung
          (Art. 17), Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) sowie
          Widerspruch (Art. 21). Anfragen von Mitarbeitenden eines Kundenunternehmens richten sich in der
          Regel zunächst an den Arbeitgeber (Verantwortlicher); alternativ nehmen wir Anfragen unter{' '}
          mahmood.aldjabboori@gmail.com entgegen und leiten sie ggf. weiter. Darüber hinaus besteht ein
          Beschwerderecht bei einer Datenschutzaufsichtsbehörde.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>8. Kontakt</h2>
        <p>Für Fragen zum Datenschutz wende dich an: mahmood.aldjabboori@gmail.com.</p>
      </div>
    </LegalPage>
  );
}
