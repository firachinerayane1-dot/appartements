# Configuration de la connexion Google

1. Dans Google Cloud Console, créez ou sélectionnez un projet.
2. Configurez l'écran de consentement OAuth.
3. Créez un identifiant OAuth de type **Application Web**.
4. Pour le développement local, ajoutez :
   - origines JavaScript autorisées :
     - `http://127.0.0.1:8000`
     - `http://localhost:8000`
   - URI de redirection autorisées :
     - `http://127.0.0.1:8000/accounts/google/login/callback/`
     - `http://localhost:8000/accounts/google/login/callback/`
5. Copiez l'identifiant et le secret dans `.env` :

```env
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
```

6. Installez les dépendances et appliquez les migrations :

```bash
pip install -r requirements.txt
python manage.py migrate
```

Le bouton Google reste volontairement désactivé tant que les deux variables ne sont pas configurées.
En production, ajoutez également l'origine HTTPS et l'URI de callback HTTPS de
votre domaine en conservant le chemin `/accounts/google/login/callback/`.
