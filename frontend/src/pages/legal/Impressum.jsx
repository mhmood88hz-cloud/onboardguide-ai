import LegalPage, { legalStyles as s } from './LegalPage';

export default function Impressum() {
  return (
    <LegalPage title="Impressum" updatedAt="23.09.2026">
      <p>Angaben gemäß § 5 TMG / § 18 Abs. 2 MStV.</p>

      <div>
        <h2 style={s.h2}>Anbieter</h2>
        <p>
          Mahmood AL-Djabboori<br />
          [TODO: Straße und Hausnummer]<br />
          38524 Sassenburg<br />
          Deutschland
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Kontakt</h2>
        <p>
          E-Mail: mahmood.aldjabboori@gmail.com<br />
          Telefon: 0176 565199632
        </p>
      </div>

      <div>
        <h2 style={s.h2}>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2>
        <p>Mahmood AL-Djabboori, Anschrift wie oben</p>
      </div>

      <div>
        <h2 style={s.h2}>Streitschlichtung</h2>
        <p>
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{' '}
          <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer" style={s.a}>
            https://ec.europa.eu/consumers/odr/
          </a>
          . Wir sind zur Teilnahme an einem Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle
          nicht verpflichtet und nehmen an einem solchen Verfahren nicht teil.
        </p>
      </div>
    </LegalPage>
  );
}
