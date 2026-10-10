import LegalPage, { legalStyles as s } from './LegalPage';

export default function FAQ() {
  return (
    <LegalPage title="Häufige Fragen" updatedAt="10.10.2026">
      <div>
        <h2 style={s.h2}>Wer ist für meine Daten verantwortlich — mein Arbeitgeber oder OnboardGuide AI?</h2>
        <p>
          Dein Arbeitgeber (das Kundenunternehmen). OnboardGuide AI verarbeitet deine Daten nur als
          Auftragsverarbeiter im Auftrag deiner Firma (Art. 28 DSGVO) — Fragen zu deinen Daten
          richten sich daher zunächst an deinen Arbeitgeber, nicht an uns direkt. Details in der{' '}
          <a href="/datenschutz" style={s.a}>Datenschutzerklärung</a>.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Woher weiß die KI, was sie antworten soll — erfindet sie Antworten?</h2>
        <p>
          Nein. Die KI antwortet ausschließlich auf Basis der Dokumente, die deine Firma selbst
          hochgeladen hat (Handbuch, Richtlinien, Projektpläne) — per RAG (Retrieval-Augmented
          Generation) werden die relevantesten Abschnitte gesucht und als Grundlage für die Antwort
          verwendet. Keine generischen Internet-Antworten, keine erfundenen Inhalte.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Sieht mein Vorgesetzter oder die Verwaltung meinen Chatverlauf?</h2>
        <p>
          Nach aktuellem Funktionsumfang nicht — es gibt keine Funktion, über die Leader oder
          Verwaltung den Chatverlauf anderer Mitarbeitender einsehen können. Sichtbar für Leader/
          Verwaltung sind Aufgabenstatus und Team-Fortschritt, nicht einzelne Chat-Nachrichten.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Können andere Firmen auf unsere Dokumente oder Daten zugreifen?</h2>
        <p>
          Nein. OnboardGuide AI ist mandantenfähig gebaut — jede Firma (Organization) ist technisch
          strikt von allen anderen getrennt. Nutzer:innen, Dokumente, Chatverläufe und Aufgaben einer
          Firma sind für andere Firmen unter keinen Umständen einsehbar.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Werden unsere Dokumente zum Training von KI-Modellen verwendet?</h2>
        <p>
          Nein. Hochgeladene Dokumente und Chat-Inhalte werden nicht zum Training der eingesetzten
          Drittanbieter-Modelle (OpenAI) verwendet.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Wo werden unsere Dokumente gespeichert?</h2>
        <p>
          In einem privaten, S3-kompatiblen Objekt-Speicher (Cloudflare R2) — nicht öffentlich
          erreichbar. Lokal (Entwicklung/Tests) fällt das System automatisch auf lokalen
          Festplattenspeicher zurück.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Wie lange werden unsere Daten gespeichert?</h2>
        <p>
          Für die Dauer des Vertragsverhältnisses zwischen deiner Firma und uns. Nach Vertragsende
          bzw. auf Anfrage deiner Firma werden die Daten gelöscht, soweit keine gesetzlichen
          Aufbewahrungspflichten entgegenstehen.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Was kostet OnboardGuide AI, und was passiert nach der Testphase?</h2>
        <p>
          Eine neu registrierte Firma bekommt automatisch eine aktive Testphase (kein Stripe, keine
          Kreditkarte nötig). Soll die Nutzung dauerhaft weiterlaufen, wird das außerhalb der App
          vereinbart (Rechnung oder Lastschrift) — danach schalten wir das Konto manuell frei.
          Details und der aktuelle Preis pro Mitarbeiter:in stehen in den <a href="/agb" style={s.a}>AGB</a>.
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Wer kann meine Zugangsdaten zurücksetzen, wenn ich mein Passwort vergessen habe?</h2>
        <p>
          Verwaltung und Leader können Passwörter von Mitarbeitenden ihrer Firma zurücksetzen —
          wende dich dafür an deine HR-/Verwaltungsabteilung.
        </p>
      </div>

      <p>
        Weitere Fragen? Kontakt siehe <a href="/impressum" style={s.a}>Impressum</a>. Rechtliche
        Details zusätzlich in <a href="/agb" style={s.a}>AGB</a> und{' '}
        <a href="/datenschutz" style={s.a}>Datenschutzerklärung</a>.
      </p>
    </LegalPage>
  );
}
