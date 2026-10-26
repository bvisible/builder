# //// Neoffice — added file (no upstream equivalent): the privacy policy and the legal notice of a generated site, written without a model.
"""Every site Nora builds carries its privacy policy and its legal notice (2026-10-22).

Until then only a shop was given legal pages, and the model wrote them: a model of the size we run writes a privacy policy that reads
well and states what nobody checked (a retention period, a country, a provider). A policy is a document with a fixed content, set by
the law (Swiss Federal Act on Data Protection, art. 19: who is responsible, what is processed and why, who receives it, in which
country, what the visitor can ask), so it is written ONCE here, in the four languages of the generator, and filled with what the
site really does:
  - the business, from the company record (`Facts`);
  - what the pages of the site contain: a contact form, a map, a newsletter, a shop (`uses_of`), so that the policy never describes a
    processing the site does not have, and never leaves out one it has;
  - the sub-processors of Neoffice (SUBPROCESSORS), the list validated on 2026-10-07 and published at neoffice.ch/fr/sous-traitants.
Nothing the business did not give is invented: a missing contact line is a visible blank for the owner to fill in, as the legal pages
of a shop always did.

The page is built from the same nodes as a recipe (recipes.py) and goes through the same YAML as a page the model wrote, so it is
saved, linked in the footer and reviewed like any other. No model is called here. The text is a template, to be read by whoever
answers for the site: it does not replace a lawyer's opinion on a business with particular processing."""

import re
from dataclasses import dataclass

import frappe

from builder.site_ai.nora import recipes as R

PRIVACY_ROUTE = "privacy-policy"
NOTICE_ROUTE = "legal-notice"
# the routes of the pages written here (site_builder.LEGAL_ROUTES holds every spelling a site may use)
MECHANICAL_ROUTES = {PRIVACY_ROUTE: "privacy", NOTICE_ROUTE: "notice"}
LANGUAGES = ("fr", "en", "de", "it")

# Who else touches the data of a site hosted by Neoffice, and where (Neoffice/Certifications/08-Sous-Traitants-Et-Prestataires, 2026-10-07).
# One place: the day a provider changes, the policies of the sites built after it say so.
SUBPROCESSORS = {
	"host": "Infomaniak Network SA",
	"host_town": {"fr": "Genève", "en": "Geneva", "de": "Genf", "it": "Ginevra"},
	"mail": "Brevo (Sendinblue SAS)",
}

TITLES = {
	"fr": {"privacy": "Politique de confidentialité", "notice": "Mentions légales", "terms": "Conditions générales"},
	"en": {"privacy": "Privacy Policy", "notice": "Legal Notice", "terms": "Terms & Conditions"},
	"de": {"privacy": "Datenschutzerklärung", "notice": "Impressum", "terms": "Allgemeine Geschäftsbedingungen"},
	"it": {"privacy": "Informativa sulla privacy", "notice": "Note legali", "terms": "Condizioni generali"},
}

MONTHS = {
	"fr": "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split(),
	"en": "January February March April May June July August September October November December".split(),
	"de": "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split(),
	"it": "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(),
}

# {name}, {address}, {contact}, {date}, {what} are filled by `text()`; the two-letter keys are the sections of a document
TEXT = {
	"fr": {
		"blank": "[à compléter : {what}]",
		"what_contact": "adresse e-mail ou téléphone de contact",
		"what_uid": "numéro IDE (CHE-…) et numéro de TVA, le cas échéant",
		"updated": "Dernière mise à jour : {date}",
		"p_intro": "Cette déclaration explique quelles données personnelles {name} traite lorsque vous visitez ce site, pourquoi, et quels sont vos droits. Elle est établie selon la loi fédérale suisse sur la protection des données (LPD) et, dans la mesure où il s'applique, le règlement général sur la protection des données de l'Union européenne (RGPD).",
		"p_controller_h": "Responsable du traitement",
		"p_controller": "{name}{address}. Pour toute question sur vos données personnelles : {contact}.",
		"p_visit_h": "Visite du site",
		"p_visit": "Lorsque vous consultez ce site, le serveur qui l'héberge enregistre automatiquement des données techniques : votre adresse IP, la date et l'heure de la visite, la page demandée et le type de navigateur. Ces données sont nécessaires pour afficher le site, le sécuriser et le faire fonctionner. Elles ne servent ni à vous identifier ni à établir un profil.",
		"p_cookies_h": "Cookies",
		"p_cookies": "Ce site n'utilise que des cookies techniques, indispensables à son fonctionnement (par exemple une session anonyme et vos préférences d'affichage). Il ne pose aucun cookie de mesure d'audience, de publicité ou de réseau social. Le choix que vous faites en fermant l'information sur les cookies est conservé dans votre navigateur.",
		"p_form_h": "Formulaires de contact",
		"p_form": "Si vous nous écrivez par un formulaire du site, nous traitons les informations que vous y saisissez (par exemple votre nom, votre adresse e-mail, votre numéro de téléphone et votre message) uniquement pour répondre à votre demande. Elles sont conservées le temps nécessaire au traitement de votre demande, puis aussi longtemps que la loi ou nos obligations l'exigent.",
		"p_form_ai": "Selon la configuration du site, les messages peuvent être lus par un assistant automatisé (intelligence artificielle) qui en rédige un résumé pour faciliter leur traitement. Cet assistant fonctionne sur des serveurs situés en Suisse et ne prend aucune décision à votre sujet : c'est une personne qui répond à votre message.",
		"p_news_h": "Lettre d'information",
		"p_news": "Si vous vous inscrivez à notre lettre d'information, nous utilisons votre adresse e-mail pour vous l'envoyer. Vous pouvez vous désinscrire à tout moment, par le lien présent dans chaque envoi ou en nous écrivant.",
		"p_shop_h": "Compte client, commandes et paiements",
		"p_cookies_shop": "Sur ce site de vente, la connexion à votre compte et votre panier utilisent aussi un cookie technique, supprimé à la fin de la session ou à la déconnexion.",
		"p_shop": "Si vous demandez un compte ou passez commande, nous traitons les données nécessaires à l'exécution du contrat : votre identité, vos adresses de facturation et de livraison, vos coordonnées et le contenu de votre commande. Le paiement est traité par le prestataire de paiement que vous choisissez au moment de la commande, qui est responsable de ses propres traitements. Les pièces comptables sont conservées dix ans, comme la loi suisse l'exige.",
		"p_map_h": "Carte",
		"p_map": "La carte Google Maps n'est chargée qu'avec votre accord : lorsque vous acceptez dans le bandeau d'information, ou lorsque vous cliquez sur « Afficher la carte ». Votre adresse IP et des données techniques sont alors transmises à Google, aux États-Unis, qui peut en déduire que vous avez consulté cette page. Vous pouvez retirer votre accord à tout moment sous la carte (« Ne plus afficher la carte automatiquement »). Tant que vous n'avez ni accepté ni cliqué, aucune donnée n'est transmise à Google.",
		"p_recip_h": "Destinataires et hébergement",
		"p_recip": "Nous ne vendons pas vos données. Elles ne sont communiquées qu'à nos prestataires, pour faire fonctionner ce site : l'hébergement est assuré par {host} ({host_town}, Suisse) et les e-mails de notification peuvent être acheminés par {mail} (France).",
		"p_abroad_h": "Transferts à l'étranger",
		"p_abroad": "Vos données sont traitées en Suisse. Les e-mails de notification transitent par la France, un pays reconnu par la Suisse comme offrant une protection adéquate.",
		"p_abroad_map": " Seule exception : l'affichage de la carte, décrit ci-dessus, qui transmet des données à Google aux États-Unis.",
		"p_abroad_shop": " Le prestataire de paiement que vous choisissez peut traiter vos données à l'étranger ; il vous en informe lors du paiement.",
		"p_rights_h": "Vos droits",
		"p_rights": "Vous pouvez demander l'accès à vos données, leur rectification ou leur effacement, vous opposer à leur traitement, en demander la limitation ou la remise dans un format courant, et retirer à tout moment un consentement que vous avez donné. Écrivez-nous : {contact}. Nous répondons dans un délai de 30 jours. Si vous estimez que vos droits ne sont pas respectés, vous pouvez vous adresser au Préposé fédéral à la protection des données et à la transparence (PFPDT, www.edoeb.admin.ch) ou, si vous résidez dans l'Union européenne, à l'autorité de protection des données de votre pays.",
		"p_sec_h": "Sécurité",
		"p_sec": "Le site est servi par une connexion chiffrée (HTTPS) et les données sont stockées sur des serveurs protégés. Aucune transmission par Internet n'est cependant totalement sûre.",
		"p_chg_h": "Modifications",
		"p_chg": "Nous pouvons adapter cette déclaration, par exemple lorsque le site change. La version publiée sur cette page est la version en vigueur.",
		"n_publisher_h": "Éditeur du site",
		"n_address": "Adresse : {address}",
		"n_email": "E-mail : {email}",
		"n_phone": "Téléphone : {phone}",
		"n_website": "Site web : {website}",
		"n_uid": "N° IDE et TVA : {blank}",
		"n_content_h": "Responsable du contenu",
		"n_content": "{name}.",
		"n_hosting_h": "Hébergement",
		"n_hosting": "Ce site est hébergé par {host}, {host_town} (Suisse).",
		"n_ip_h": "Propriété intellectuelle",
		"n_ip": "Les textes, images, logos et autres contenus de ce site sont protégés par le droit d'auteur et appartiennent à {name} ou à leurs titulaires respectifs. Toute reproduction, modification ou diffusion sans autorisation écrite préalable est interdite.",
		"n_liab_h": "Exclusion de responsabilité",
		"n_liab": "Nous apportons le plus grand soin à l'exactitude des informations de ce site, sans pouvoir la garantir. Nous déclinons toute responsabilité pour les dommages liés à leur utilisation, dans la mesure permise par la loi. Les liens vers des sites tiers sont fournis pour votre commodité : nous n'avons aucune influence sur leur contenu et déclinons toute responsabilité à leur égard.",
		"n_data_h": "Protection des données",
		"n_data": "Le traitement de vos données personnelles est décrit dans notre politique de confidentialité.",
		"n_data_link": "Lire la politique de confidentialité",
		"n_law_h": "Droit applicable",
		"n_law": "Le droit suisse est applicable.",
	},
	"en": {
		"blank": "[to be completed: {what}]",
		"what_contact": "contact e-mail address or phone number",
		"what_uid": "company identification number (CHE-…) and VAT number, if any",
		"updated": "Last updated: {date}",
		"p_intro": "This statement explains which personal data {name} processes when you visit this website, why, and what your rights are. It is drawn up under the Swiss Federal Act on Data Protection (FADP) and, where it applies, the European Union's General Data Protection Regulation (GDPR).",
		"p_controller_h": "Controller",
		"p_controller": "{name}{address}. For any question about your personal data: {contact}.",
		"p_visit_h": "Visiting the website",
		"p_visit": "When you visit this website, the server that hosts it automatically records technical data: your IP address, the date and time of the visit, the page requested and the type of browser. This data is needed to display the website, keep it secure and make it work. It is not used to identify you or to build a profile.",
		"p_cookies_h": "Cookies",
		"p_cookies": "This website only uses technical cookies, which are essential to its operation (for example an anonymous session and your display preferences). It sets no audience-measurement, advertising or social-network cookies. The choice you make by closing the cookie notice is kept in your browser.",
		"p_form_h": "Contact forms",
		"p_form": "If you write to us through a form on the website, we process the information you enter (for example your name, e-mail address, phone number and message) only to answer your request. It is kept for as long as needed to handle your request, and then for as long as the law or our obligations require.",
		"p_form_ai": "Depending on how the website is set up, messages may be read by an automated assistant (artificial intelligence) that writes a summary to make them easier to handle. This assistant runs on servers located in Switzerland and takes no decision about you: a person answers your message.",
		"p_news_h": "Newsletter",
		"p_news": "If you subscribe to our newsletter, we use your e-mail address to send it to you. You can unsubscribe at any time, with the link in every issue or by writing to us.",
		"p_shop_h": "Customer account, orders and payments",
		"p_cookies_shop": "On this shop, signing in to your account and your basket also use a technical cookie, removed at the end of the session or when you sign out.",
		"p_shop": "If you request an account or place an order, we process the data needed to perform the contract: your identity, your billing and delivery addresses, your contact details and the content of your order. Payment is handled by the payment provider you choose when you order, which is responsible for its own processing. Accounting records are kept for ten years, as Swiss law requires.",
		"p_map_h": "Map",
		"p_map": "The Google Maps map is loaded only with your agreement: when you accept in the information banner, or when you click “Show the map”. Your IP address and technical data are then sent to Google, in the United States, which can tell that you viewed this page. You can withdraw your agreement at any time under the map (“Stop showing the map automatically”). As long as you have neither accepted nor clicked, no data is sent to Google.",
		"p_recip_h": "Recipients and hosting",
		"p_recip": "We do not sell your data. It is shared only with our providers, to run this website: hosting is provided by {host} ({host_town}, Switzerland) and notification e-mails may be delivered by {mail} (France).",
		"p_abroad_h": "Transfers abroad",
		"p_abroad": "Your data is processed in Switzerland. Notification e-mails pass through France, a country that Switzerland recognises as offering adequate protection.",
		"p_abroad_map": " The only exception is the display of the map, described above, which sends data to Google in the United States.",
		"p_abroad_shop": " The payment provider you choose may process your data abroad; it informs you when you pay.",
		"p_rights_h": "Your rights",
		"p_rights": "You can ask for access to your data, for its correction or erasure, object to its processing, ask for it to be restricted or handed over in a common format, and withdraw at any time a consent you have given. Write to us: {contact}. We answer within 30 days. If you believe your rights are not respected, you can contact the Swiss Federal Data Protection and Information Commissioner (FDPIC, www.edoeb.admin.ch) or, if you live in the European Union, the data protection authority of your country.",
		"p_sec_h": "Security",
		"p_sec": "The website is served over an encrypted connection (HTTPS) and the data is stored on protected servers. No transmission over the Internet is ever completely secure, however.",
		"p_chg_h": "Changes",
		"p_chg": "We may update this statement, for example when the website changes. The version published on this page is the one in force.",
		"n_publisher_h": "Publisher",
		"n_address": "Address: {address}",
		"n_email": "E-mail: {email}",
		"n_phone": "Phone: {phone}",
		"n_website": "Website: {website}",
		"n_uid": "Company ID and VAT: {blank}",
		"n_content_h": "Responsible for the content",
		"n_content": "{name}.",
		"n_hosting_h": "Hosting",
		"n_hosting": "This website is hosted by {host}, {host_town} (Switzerland).",
		"n_ip_h": "Intellectual property",
		"n_ip": "The texts, images, logos and other content of this website are protected by copyright and belong to {name} or to their respective owners. Any reproduction, modification or distribution without prior written permission is prohibited.",
		"n_liab_h": "Disclaimer",
		"n_liab": "We take great care over the accuracy of the information on this website, without being able to guarantee it. We accept no liability for damage arising from its use, to the extent the law allows. Links to third-party websites are provided for your convenience: we have no influence over their content and accept no liability for it.",
		"n_data_h": "Data protection",
		"n_data": "The processing of your personal data is described in our privacy policy.",
		"n_data_link": "Read the privacy policy",
		"n_law_h": "Applicable law",
		"n_law": "Swiss law applies.",
	},
	"de": {
		"blank": "[zu ergänzen: {what}]",
		"what_contact": "Kontakt-E-Mail-Adresse oder Telefonnummer",
		"what_uid": "UID-Nummer (CHE-…) und MWST-Nummer, falls vorhanden",
		"updated": "Letzte Aktualisierung: {date}",
		"p_intro": "Diese Erklärung beschreibt, welche Personendaten {name} bearbeitet, wenn Sie diese Website besuchen, wozu und welche Rechte Sie haben. Sie stützt sich auf das schweizerische Bundesgesetz über den Datenschutz (DSG) und, soweit anwendbar, auf die Datenschutz-Grundverordnung der Europäischen Union (DSGVO).",
		"p_controller_h": "Verantwortliche Stelle",
		"p_controller": "{name}{address}. Bei Fragen zu Ihren Personendaten: {contact}.",
		"p_visit_h": "Besuch der Website",
		"p_visit": "Wenn Sie diese Website besuchen, erfasst der Server, der sie hostet, automatisch technische Daten: Ihre IP-Adresse, Datum und Uhrzeit des Besuchs, die aufgerufene Seite und den Browsertyp. Diese Daten sind nötig, um die Website anzuzeigen, zu sichern und zu betreiben. Sie dienen weder dazu, Sie zu identifizieren, noch dazu, ein Profil zu erstellen.",
		"p_cookies_h": "Cookies",
		"p_cookies": "Diese Website verwendet nur technische Cookies, die für ihren Betrieb unerlässlich sind (zum Beispiel eine anonyme Sitzung und Ihre Anzeigeeinstellungen). Sie setzt keine Cookies zur Reichweitenmessung, für Werbung oder für soziale Netzwerke. Ihre Wahl beim Schliessen des Cookie-Hinweises wird in Ihrem Browser gespeichert.",
		"p_form_h": "Kontaktformulare",
		"p_form": "Wenn Sie uns über ein Formular der Website schreiben, bearbeiten wir die Angaben, die Sie eingeben (zum Beispiel Ihren Namen, Ihre E-Mail-Adresse, Ihre Telefonnummer und Ihre Nachricht), nur um Ihre Anfrage zu beantworten. Sie werden so lange aufbewahrt, wie es für die Bearbeitung Ihrer Anfrage nötig ist, danach so lange, wie das Gesetz oder unsere Pflichten es verlangen.",
		"p_form_ai": "Je nach Einrichtung der Website können Nachrichten von einem automatisierten Assistenten (künstliche Intelligenz) gelesen werden, der eine Zusammenfassung verfasst, um die Bearbeitung zu erleichtern. Dieser Assistent läuft auf Servern in der Schweiz und trifft keine Entscheidung über Sie: Eine Person beantwortet Ihre Nachricht.",
		"p_news_h": "Newsletter",
		"p_news": "Wenn Sie unseren Newsletter abonnieren, verwenden wir Ihre E-Mail-Adresse, um ihn Ihnen zuzustellen. Sie können sich jederzeit abmelden, über den Link in jeder Ausgabe oder indem Sie uns schreiben.",
		"p_shop_h": "Kundenkonto, Bestellungen und Zahlungen",
		"p_cookies_shop": "In diesem Shop verwenden die Anmeldung bei Ihrem Konto und Ihr Warenkorb ebenfalls ein technisches Cookie, das am Ende der Sitzung oder beim Abmelden gelöscht wird.",
		"p_shop": "Wenn Sie ein Konto beantragen oder bestellen, bearbeiten wir die Daten, die für die Vertragserfüllung nötig sind: Ihre Identität, Ihre Rechnungs- und Lieferadresse, Ihre Kontaktangaben und den Inhalt Ihrer Bestellung. Die Zahlung wird vom Zahlungsdienstleister abgewickelt, den Sie bei der Bestellung wählen und der für seine eigenen Bearbeitungen verantwortlich ist. Buchungsbelege werden, wie vom schweizerischen Recht verlangt, zehn Jahre aufbewahrt.",
		"p_map_h": "Karte",
		"p_map": "Die Google-Maps-Karte wird nur mit Ihrer Zustimmung geladen: wenn Sie im Informationshinweis zustimmen oder auf «Karte anzeigen» klicken. Ihre IP-Adresse und technische Daten werden dann an Google in den USA übermittelt, wo erkannt werden kann, dass Sie diese Seite besucht haben. Sie können Ihre Zustimmung jederzeit unter der Karte widerrufen («Karte nicht mehr automatisch anzeigen»). Solange Sie weder zugestimmt noch geklickt haben, werden keine Daten an Google übermittelt.",
		"p_recip_h": "Empfänger und Hosting",
		"p_recip": "Wir verkaufen Ihre Daten nicht. Sie werden nur an unsere Dienstleister weitergegeben, damit diese Website funktioniert: Das Hosting erfolgt durch {host} ({host_town}, Schweiz), und Benachrichtigungs-E-Mails können über {mail} (Frankreich) zugestellt werden.",
		"p_abroad_h": "Übermittlung ins Ausland",
		"p_abroad": "Ihre Daten werden in der Schweiz bearbeitet. Benachrichtigungs-E-Mails laufen über Frankreich, ein Land, dem die Schweiz einen angemessenen Datenschutz bescheinigt.",
		"p_abroad_map": " Einzige Ausnahme ist die oben beschriebene Anzeige der Karte, bei der Daten an Google in den USA übermittelt werden.",
		"p_abroad_shop": " Der von Ihnen gewählte Zahlungsdienstleister kann Ihre Daten im Ausland bearbeiten; er informiert Sie bei der Zahlung.",
		"p_rights_h": "Ihre Rechte",
		"p_rights": "Sie können Auskunft über Ihre Daten verlangen, deren Berichtigung oder Löschung, der Bearbeitung widersprechen, ihre Einschränkung oder die Herausgabe in einem gängigen Format verlangen und eine erteilte Einwilligung jederzeit widerrufen. Schreiben Sie uns: {contact}. Wir antworten innert 30 Tagen. Wenn Sie der Ansicht sind, dass Ihre Rechte nicht gewahrt werden, können Sie sich an den Eidgenössischen Datenschutz- und Öffentlichkeitsbeauftragten (EDÖB, www.edoeb.admin.ch) oder, wenn Sie in der Europäischen Union wohnen, an die Datenschutzbehörde Ihres Landes wenden.",
		"p_sec_h": "Sicherheit",
		"p_sec": "Die Website wird über eine verschlüsselte Verbindung (HTTPS) ausgeliefert, und die Daten liegen auf geschützten Servern. Keine Übertragung über das Internet ist jedoch vollkommen sicher.",
		"p_chg_h": "Änderungen",
		"p_chg": "Wir können diese Erklärung anpassen, zum Beispiel wenn sich die Website ändert. Es gilt die auf dieser Seite veröffentlichte Fassung.",
		"n_publisher_h": "Anbieter der Website",
		"n_address": "Adresse: {address}",
		"n_email": "E-Mail: {email}",
		"n_phone": "Telefon: {phone}",
		"n_website": "Website: {website}",
		"n_uid": "UID und MWST: {blank}",
		"n_content_h": "Verantwortlich für den Inhalt",
		"n_content": "{name}.",
		"n_hosting_h": "Hosting",
		"n_hosting": "Diese Website wird von {host}, {host_town} (Schweiz), gehostet.",
		"n_ip_h": "Geistiges Eigentum",
		"n_ip": "Die Texte, Bilder, Logos und übrigen Inhalte dieser Website sind urheberrechtlich geschützt und gehören {name} oder den jeweiligen Rechteinhabern. Jede Vervielfältigung, Änderung oder Verbreitung ohne vorherige schriftliche Genehmigung ist untersagt.",
		"n_liab_h": "Haftungsausschluss",
		"n_liab": "Wir achten sehr auf die Richtigkeit der Informationen dieser Website, können sie aber nicht garantieren. Wir lehnen jede Haftung für Schäden aus ihrer Nutzung ab, soweit das Gesetz es erlaubt. Links zu Websites Dritter dienen Ihrer Bequemlichkeit: Auf deren Inhalt haben wir keinen Einfluss und lehnen jede Haftung dafür ab.",
		"n_data_h": "Datenschutz",
		"n_data": "Die Bearbeitung Ihrer Personendaten ist in unserer Datenschutzerklärung beschrieben.",
		"n_data_link": "Datenschutzerklärung lesen",
		"n_law_h": "Anwendbares Recht",
		"n_law": "Es gilt schweizerisches Recht.",
	},
	"it": {
		"blank": "[da completare: {what}]",
		"what_contact": "indirizzo e-mail o numero di telefono di contatto",
		"what_uid": "numero IDI (CHE-…) e numero IVA, se presenti",
		"updated": "Ultimo aggiornamento: {date}",
		"p_intro": "Questa informativa spiega quali dati personali {name} tratta quando visitate questo sito, perché e quali sono i vostri diritti. È redatta in base alla legge federale svizzera sulla protezione dei dati (LPD) e, nella misura in cui si applica, al regolamento generale sulla protezione dei dati dell'Unione europea (RGPD).",
		"p_controller_h": "Titolare del trattamento",
		"p_controller": "{name}{address}. Per qualsiasi domanda sui vostri dati personali: {contact}.",
		"p_visit_h": "Visita del sito",
		"p_visit": "Quando visitate questo sito, il server che lo ospita registra automaticamente dati tecnici: il vostro indirizzo IP, la data e l'ora della visita, la pagina richiesta e il tipo di browser. Questi dati sono necessari per mostrare il sito, proteggerlo e farlo funzionare. Non servono né a identificarvi né a creare un profilo.",
		"p_cookies_h": "Cookie",
		"p_cookies": "Questo sito utilizza soltanto cookie tecnici, indispensabili al suo funzionamento (ad esempio una sessione anonima e le vostre preferenze di visualizzazione). Non installa cookie di misurazione dell'audience, pubblicitari o di reti sociali. La scelta che fate chiudendo l'avviso sui cookie è conservata nel vostro browser.",
		"p_form_h": "Moduli di contatto",
		"p_form": "Se ci scrivete tramite un modulo del sito, trattiamo le informazioni che inserite (ad esempio nome, indirizzo e-mail, numero di telefono e messaggio) soltanto per rispondere alla vostra richiesta. Sono conservate per il tempo necessario a gestire la richiesta e poi per il tempo richiesto dalla legge o dai nostri obblighi.",
		"p_form_ai": "A seconda della configurazione del sito, i messaggi possono essere letti da un assistente automatizzato (intelligenza artificiale) che ne redige un riassunto per facilitarne la gestione. Questo assistente funziona su server situati in Svizzera e non prende alcuna decisione su di voi: è una persona a rispondere al vostro messaggio.",
		"p_news_h": "Newsletter",
		"p_news": "Se vi iscrivete alla nostra newsletter, utilizziamo il vostro indirizzo e-mail per inviarvela. Potete annullare l'iscrizione in qualsiasi momento, tramite il link presente in ogni invio o scrivendoci.",
		"p_shop_h": "Account cliente, ordini e pagamenti",
		"p_cookies_shop": "In questo negozio, l'accesso al vostro account e il carrello utilizzano anch'essi un cookie tecnico, eliminato al termine della sessione o alla disconnessione.",
		"p_shop": "Se richiedete un account o effettuate un ordine, trattiamo i dati necessari all'esecuzione del contratto: la vostra identità, gli indirizzi di fatturazione e di consegna, i recapiti e il contenuto dell'ordine. Il pagamento è gestito dal fornitore di servizi di pagamento che scegliete al momento dell'ordine, responsabile dei propri trattamenti. I documenti contabili sono conservati per dieci anni, come richiede il diritto svizzero.",
		"p_map_h": "Mappa",
		"p_map": "La mappa di Google Maps viene caricata solo con il vostro consenso: quando accettate nell'avviso informativo o cliccate su «Mostra la mappa». Il vostro indirizzo IP e dati tecnici sono allora trasmessi a Google, negli Stati Uniti, che può dedurne che avete consultato questa pagina. Potete ritirare il consenso in qualsiasi momento sotto la mappa («Non mostrare più la mappa automaticamente»). Finché non avete né accettato né cliccato, nessun dato è trasmesso a Google.",
		"p_recip_h": "Destinatari e hosting",
		"p_recip": "Non vendiamo i vostri dati. Sono comunicati solo ai nostri fornitori, per far funzionare questo sito: l'hosting è assicurato da {host} ({host_town}, Svizzera) e le e-mail di notifica possono essere recapitate da {mail} (Francia).",
		"p_abroad_h": "Trasferimenti all'estero",
		"p_abroad": "I vostri dati sono trattati in Svizzera. Le e-mail di notifica transitano dalla Francia, un paese che la Svizzera riconosce come garante di una protezione adeguata.",
		"p_abroad_map": " Unica eccezione: la visualizzazione della mappa, descritta sopra, che trasmette dati a Google negli Stati Uniti.",
		"p_abroad_shop": " Il fornitore di pagamento che scegliete può trattare i vostri dati all'estero; vi informa al momento del pagamento.",
		"p_rights_h": "I vostri diritti",
		"p_rights": "Potete chiedere l'accesso ai vostri dati, la loro rettifica o cancellazione, opporvi al loro trattamento, chiederne la limitazione o la consegna in un formato comune e revocare in qualsiasi momento un consenso dato. Scriveteci: {contact}. Rispondiamo entro 30 giorni. Se ritenete che i vostri diritti non siano rispettati, potete rivolgervi all'Incaricato federale della protezione dei dati e della trasparenza (IFPDT, www.edoeb.admin.ch) o, se risiedete nell'Unione europea, all'autorità per la protezione dei dati del vostro paese.",
		"p_sec_h": "Sicurezza",
		"p_sec": "Il sito è servito tramite una connessione cifrata (HTTPS) e i dati sono conservati su server protetti. Nessuna trasmissione via Internet è però completamente sicura.",
		"p_chg_h": "Modifiche",
		"p_chg": "Possiamo adeguare questa informativa, ad esempio quando il sito cambia. La versione pubblicata su questa pagina è quella in vigore.",
		"n_publisher_h": "Editore del sito",
		"n_address": "Indirizzo: {address}",
		"n_email": "E-mail: {email}",
		"n_phone": "Telefono: {phone}",
		"n_website": "Sito web: {website}",
		"n_uid": "IDI e IVA: {blank}",
		"n_content_h": "Responsabile dei contenuti",
		"n_content": "{name}.",
		"n_hosting_h": "Hosting",
		"n_hosting": "Questo sito è ospitato da {host}, {host_town} (Svizzera).",
		"n_ip_h": "Proprietà intellettuale",
		"n_ip": "I testi, le immagini, i loghi e gli altri contenuti di questo sito sono protetti dal diritto d'autore e appartengono a {name} o ai rispettivi titolari. Qualsiasi riproduzione, modifica o diffusione senza previa autorizzazione scritta è vietata.",
		"n_liab_h": "Esclusione di responsabilità",
		"n_liab": "Poniamo la massima cura nell'esattezza delle informazioni di questo sito, senza poterla garantire. Decliniamo ogni responsabilità per i danni derivanti dal loro utilizzo, nella misura consentita dalla legge. I link a siti di terzi sono forniti per comodità: non abbiamo alcuna influenza sul loro contenuto e decliniamo ogni responsabilità al riguardo.",
		"n_data_h": "Protezione dei dati",
		"n_data": "Il trattamento dei vostri dati personali è descritto nella nostra informativa sulla privacy.",
		"n_data_link": "Leggere l'informativa sulla privacy",
		"n_law_h": "Diritto applicabile",
		"n_law": "Si applica il diritto svizzero.",
	},
}

# what a page of the site holds that the policy has to describe: the markers of the includes and of the chrome
FORM_MARKERS = ("contact_form.html", "site_form.html", '"element": "form"')
MAP_MARKERS = ("google_map.html",)


@dataclass
class Facts:
	"""What the policy and the notice say about the business and about what its site does."""

	name: str
	address: str = ""
	email: str = ""
	phone: str = ""
	website: str = ""
	form: bool = False
	map: bool = False
	newsletter: bool = False
	shop: bool = False


def language_of(lang: str | None) -> str:
	code = str(lang or "fr").strip().lower()[:2]
	return code if code in LANGUAGES else "fr"


def is_mechanical(page: dict) -> bool:
	"""Whether a planned page is written here instead of by the model: a legal page whose route is the policy or the notice."""
	return page.get("type") == "legal" and str(page.get("route") or "").strip("/").lower() in MECHANICAL_ROUTES


def kind_of(page: dict) -> str:
	return MECHANICAL_ROUTES[str(page.get("route") or "").strip("/").lower()]


def title(kind: str, lang: str) -> str:
	return TITLES[language_of(lang)][kind]


def date_text(lang: str, today) -> str:
	"""A date as the language writes it: 22 octobre 2026, October 22, 2026, 22. Oktober 2026."""
	lang = language_of(lang)
	month = MONTHS[lang][today.month - 1]
	if lang == "en":
		return f"{month} {today.day}, {today.year}"
	if lang == "de":
		return f"{today.day}. {month} {today.year}"
	day = {("fr", 1): "1er", ("it", 1): "1°"}.get((lang, today.day), str(today.day))
	return f"{day} {month} {today.year}"


def text(lang: str, key: str, facts: Facts | None = None, today=None) -> str:
	"""A paragraph of the library, filled with the facts of the business."""
	lang = language_of(lang)
	raw = TEXT[lang][key]
	blank = TEXT[lang]["blank"]
	values = {
		"host": SUBPROCESSORS["host"],
		"host_town": SUBPROCESSORS["host_town"][lang],
		"mail": SUBPROCESSORS["mail"],
		"date": date_text(lang, today) if today else "",
	}
	if facts is not None:
		contact = ", ".join(v for v in (facts.email, facts.phone) if v) or blank.format(what=TEXT[lang]["what_contact"])
		values.update(
			name=facts.name,
			address=f", {facts.address}" if facts.address else "",
			contact=contact,
			email=facts.email,
			phone=facts.phone,
			website=facts.website,
			blank=blank.format(what=TEXT[lang]["what_uid"]),
		)
	return raw.format(**values)


def uses_of(profile: str | None, site_type: str = "") -> dict:
	"""What the pages already written for this profile hold: a form, a map, a newsletter, a shop."""
	uses = {"form": False, "map": False, "newsletter": False, "shop": site_type in ("ecommerce", "ecommerce_search")}
	try:
		filters = {"published": 1}
		if profile and frappe.db.has_column("Builder Page", "neo_website_profile"):
			filters["neo_website_profile"] = profile
		for row in frappe.get_all("Builder Page", filters=filters, fields=["blocks"], limit_page_length=0):
			raw = str(row.get("blocks") or "")
			uses["form"] = uses["form"] or any(m in raw for m in FORM_MARKERS)
			uses["map"] = uses["map"] or any(m in raw for m in MAP_MARKERS)
	except Exception:
		pass
	try:
		from builder.api import _get_site_chrome_config

		config = _get_site_chrome_config(profile)
		uses["newsletter"] = bool(config and (config.get("show_newsletter") or config.get("newsletter_popup")))
	except Exception:
		pass
	return uses


def facts_from(contact: dict, site_name: str, uses: dict) -> Facts:
	"""The facts of a site, from the verified business data (api.get_site_contact_context) and from what its pages hold."""
	contact = contact or {}
	return Facts(
		name=(contact.get("company_name") or site_name or "").strip(),
		address=str(contact.get("address") or "").strip(),
		email=str(contact.get("email") or "").strip(),
		phone=str(contact.get("phone") or "").strip(),
		website=str(contact.get("website") or "").strip(),
		form=bool(uses.get("form")),
		map=bool(uses.get("map")),
		newsletter=bool(uses.get("newsletter")),
		shop=bool(uses.get("shop")),
	)


# ---------------------------------------------------------------- the documents, as sections of paragraphs


def privacy_sections(facts: Facts, lang: str, today) -> list[tuple[str, list]]:
	"""The privacy policy: (heading, paragraphs) in the order the law reads them; a heading of "" is the introduction."""
	t = lambda key: text(lang, key, facts, today)  # noqa: E731
	sections: list[tuple[str, list]] = [("", [t("updated"), t("p_intro")])]
	sections.append((t("p_controller_h"), [t("p_controller")]))
	sections.append((t("p_visit_h"), [t("p_visit")]))
	sections.append((t("p_cookies_h"), [t("p_cookies")] + ([t("p_cookies_shop")] if facts.shop else [])))
	if facts.form:
		sections.append((t("p_form_h"), [t("p_form"), t("p_form_ai")]))
	if facts.newsletter:
		sections.append((t("p_news_h"), [t("p_news")]))
	if facts.shop:
		sections.append((t("p_shop_h"), [t("p_shop")]))
	if facts.map:
		sections.append((t("p_map_h"), [t("p_map")]))
	sections.append((t("p_recip_h"), [t("p_recip")]))
	abroad = t("p_abroad") + (t("p_abroad_map") if facts.map else "") + (t("p_abroad_shop") if facts.shop else "")
	sections.append((t("p_abroad_h"), [abroad]))
	sections.append((t("p_rights_h"), [t("p_rights")]))
	sections.append((t("p_sec_h"), [t("p_sec")]))
	sections.append((t("p_chg_h"), [t("p_chg")]))
	return sections


def notice_sections(facts: Facts, lang: str, today) -> list[tuple[str, list]]:
	"""The legal notice: the lines of the publisher are a list, a row left out when the business gave none."""
	t = lambda key: text(lang, key, facts, today)  # noqa: E731
	lines = [facts.name]
	for key, value in (("n_address", facts.address), ("n_email", facts.email), ("n_phone", facts.phone), ("n_website", facts.website)):
		if value:
			lines.append(t(key))
	lines.append(t("n_uid"))
	return [
		("", [t("updated")]),
		(t("n_publisher_h"), [lines]),
		(t("n_content_h"), [t("n_content")]),
		(t("n_hosting_h"), [t("n_hosting")]),
		(t("n_ip_h"), [t("n_ip")]),
		(t("n_liab_h"), [t("n_liab")]),
		(t("n_data_h"), [t("n_data"), ("link", f"/{PRIVACY_ROUTE}", t("n_data_link"))]),
		(t("n_law_h"), [t("n_law")]),
	]


# ---------------------------------------------------------------- the page


def _nodes(sections: list, look: "R.Look") -> list:
	g = R.ground_of(look, "plain")
	out = []
	for heading, parts in sections:
		if heading:
			out.append(
				R.el(
					"h2",
					name="heading",
					style=R.flow(
						fontFamily=look.font_heading,
						fontSize="1.5rem",
						fontWeight="700",
						lineHeight="1.25",
						color=g.ink,
						margin="2.5rem 0 0.75rem",
					),
					m_style=R.flow(fontSize="1.25rem", margin="2rem 0 0.5rem"),
					text=heading,
				)
			)
		for part in parts:
			if isinstance(part, list):
				out.append(
					R.el(
						"ul",
						name="lines",
						style=R.flow(
							fontFamily=look.font_body,
							fontSize="1.0625rem",
							lineHeight="1.7",
							color=g.ink,
							margin="0 0 1rem",
							paddingLeft="1.25rem",
						),
						c=[R.el("li", name="line", text=line) for line in part],
					)
				)
			elif isinstance(part, tuple):
				_, href, label = part
				out.append(
					R.el(
						"a",
						name="link",
						attrs=R.flow(href=href),
						style=R.flow(
							fontFamily=look.font_body,
							fontSize="1.0625rem",
							fontWeight="600",
							color=g.accent if g.accent else look.primary,
							textDecoration="underline",
						),
						text=label,
					)
				)
			else:
				out.append(
					R.el(
						"p",
						name="paragraph",
						style=R.flow(
							fontFamily=look.font_body,
							fontSize="1.0625rem",
							lineHeight="1.7",
							color=g.ink,
							margin="0 0 1rem",
						),
						text=part,
					)
				)
	return out


def page_root(kind: str, facts: Facts, lang: str, handles: dict, palette: dict | None, today) -> dict:
	"""The page: one section, one column of reading across the page's width, headings and paragraphs, no ornament."""
	look = R.Look(handles, palette)
	ctx = R.Ctx(look, R.ground_of(look, "plain"), [], "", "")
	sections = privacy_sections(facts, lang, today) if kind == "privacy" else notice_sections(facts, lang, today)
	column = R.el(
		"div",
		name="reading",
		style=R.flow(width="100%", maxWidth="48rem"),
		c=_nodes(sections, look),
	)
	body = R.section(ctx, "legal-text", [R.container(ctx, [column])], pad="3rem 0 5rem", m_pad="2rem 0 3.5rem")
	return R.el("div", name="body", c=[body])


def page_yaml(kind: str, facts: Facts, lang: str, handles: dict, palette: dict | None, today) -> str:
	"""The page as the YAML a page of the model is: it goes through the same expansion and the same passes."""
	return R.to_yaml(page_root(kind, facts, lang, handles, palette, today))


def plain_text(kind: str, facts: Facts, lang: str, today) -> str:
	"""The words of a document, one paragraph a line: what the tests and the checks read."""
	sections = privacy_sections(facts, lang, today) if kind == "privacy" else notice_sections(facts, lang, today)
	lines: list[str] = []
	for heading, parts in sections:
		if heading:
			lines.append(heading)
		for part in parts:
			lines.extend(part if isinstance(part, list) else [part[2]] if isinstance(part, tuple) else [part])
	return "\n".join(lines)


def has_blank(value: str) -> bool:
	"""Whether a text still holds a blank for the owner to fill in (a visible `[… : …]`)."""
	return bool(re.search(r"\[[^\]]+:[^\]]+\]", value))
