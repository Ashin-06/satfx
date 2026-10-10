# 05 · Legal and Ethical Ground Rules

Not legal advice.

## Lab rules
1. **Never trigger a real emergency.** Use Apple's Emergency SOS **demo** and Google's test flow only. A real SOS reaches emergency services and a relay centre; misuse can be a criminal offence and diverts rescue resources.
2. Messages via satellite only between project phones and lab accounts.
3. Ground truth (GPS, time, sky photos) recorded for every session; no third parties in photos.
4. Satellite features may need a paid plan or a carrier opt-in. Use project accounts.

## Evidence and privacy
- Satellite SOS sends name, phone number, location, emergency contacts, medical ID and device info to emergency services and the satellite operator ([Pixel disclosure via PhoneArena](https://phonearena.com/news/google-messages-leak-hints-at-satellite-messaging-allowing-you-to-text-anyone-anywhere_id156929); Apple support pages). That data is at the provider and the PSAP; get it by legal process, not from the device alone.
- Orbital elements are public. Corroboration uses only the event time and the claimed location, which the examiner already has lawfully.
- Report orbital results as **consistency** findings with their assumptions (mask, element-set age, no terrain model), never as proof that a message was sent.

## Standards
ISO/IEC 27037, NIST SP 800-86, SWGDE mobile device guidance. Keep every element-set file used, with its source URL, download time and hash, so the computation can be reproduced.
