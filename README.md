<div align="center">
 <img src="https://gykhamine.github.io/GCI/statics/3.png" alt="Logo Gykhamine Studio" width="150" style="margin-bottom: 10px;" />
 <h1>Gykhamine Studio v3.3.1</h1>
 <p><i>Le tableau de bord visuel ultime pour piloter vos projets Django, gérer votre infrastructure et coder sans friction.</i></p>
 <p>Développé pour le projet GCI — Brazzaville, Congo.</p>
 <br>
 <a href="https://github.com/gykhamine/Boutique_erp">
 <img src="https://img.shields.io/badge/Voir_le_projet_de_base-Boutique_ERP-blue?style=for-the-badge&logo=github" alt="Lien vers Boutique ERP" />
 </a>
 </div>
<br>
<div style="background-color: #f6f8fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007acc;">
 <h3 style="margin-top: 0;">Le mot du développeur</h3>
 <p>Si vous lisez ce fichier, c'est probablement qu'on vous a demandé de travailler sur le projet <b>Boutique ERP</b>, ou que vous voulez simplement comprendre comment on gère une application web moderne ET son infrastructure sans passer trois ans à apprendre l'informatique.</p>
 <p>Franchement, le code pur, c'est très bien pour les machines, mais pour nous humains, c'est souvent un mur de texte illisible où une seule virgule mal placée peut tout casser. <b>Gykhamine Studio v3.3.1</b> a été créé pour régler ce problème. Ce n'est plus seulement un éditeur de code, c'est un véritable centre de commande.</p>
 <p>Vous n'avez pas à mémoriser la syntaxe du Python, les commandes Linux complexes ou la configuration Nginx. Vous avez juste à cliquer sur les bons boutons, modifier le texte qui vous intéresse, et laisser le logiciel s'occuper de la plomberie (Git, Bases de données, Serveurs, SSL).</p>
 <p>Ce guide n'est pas un manuel technique ennuyeux. C'est le carnet de survie que j'aurais aimé avoir quand j'ai commencé. Prenez un café, lisez-le tranquillement, et vous verrez que piloter un ERP et son serveur, c'est finalement assez simple.</p>
 </div>
<br>
<details>
 <summary><b>📖 Sommaire du guide (cliquez pour déplier)</b></summary>
 <br>
 <ul>
 <li><a href="#1-le-projet-de-base--boutique-erp">1. Le projet de base : Boutique ERP</a></li>
 <li><a href="#2-ce-quil-vous-faut-vraiment">2. Ce qu'il vous faut vraiment</a></li>
 <li><a href="#3-linstallation-sans-mal-de-tête">3. L'installation sans mal de tête</a></li>
 <li><a href="#4-tour-de-propriétaire-linterface-v331">4. Tour de propriétaire : l'interface v3.3.1</a></li>
 <li><a href="#5-comprendre-django-sans-être-ingénieur">5. Comprendre Django sans être ingénieur</a></li>
 <li><a href="#6-outils-devops-et-infrastructure-intégrés">6. Outils DevOps et Infrastructure Intégrés</a></li>
 <li><a href="#7-intelligence-artificielle-locale">7. Intelligence Artificielle Locale</a></li>
 <li><a href="#8-outils-systeme-et-developpement">8. Outils Système et Développement (C/C++, Git, Venv)</a></li>
 <li><a href="#9-scénarios-pratiques-de-la-vie-réelle">9. Scénarios pratiques de la vie réelle</a></li>
 <li><a href="#10-glossaire-de-survie">10. Glossaire de survie</a></li>
 </ul>
 </details>
<br>
<h2 id="1-le-projet-de-base--boutique-erp">1. Le projet de base : Boutique ERP</h2>
Vous n'allez pas créer un projet à partir de zéro. Ce serait une perte de temps et d'énergie. Le cœur de votre travail va se faire sur une base existante, un ERP (Progiciel de Gestion Intégré) complet qui gère une boutique, les stocks, les clients, et les factures.
Tout le code de ce projet de référence est hébergé ici : <b>https://github.com/gykhamine/Boutique_erp</b>
C'est ce qu'on appelle une "Capsule Gykhamine". C'est un projet Django pré-configuré, propre, et prêt à être modifié via le Studio. Votre rôle n'est pas de réinventer la roue, mais de personnaliser cette boutique, d'ajouter des fonctionnalités spécifiques à votre contexte local à Brazzaville, ou de corriger des bugs visuels. Le Studio est la télécommande de ce projet.
<h2 id="3-linstallation-sans-mal-de-tête">2. L'installation sans mal de tête</h2>
<h3>Étape A : Récupérer le Studio et le Projet</h3>
Maintenant, il faut télécharger le logiciel lui-même et le projet Boutique ERP.
<ol>
<li>Allez sur la page <a href="https://github.com/gykhamine/Gykhamine"><b>Gykhamine-studio</b></a></li>
 <li>Cliquez sur le bouton vert "Code", puis "Download ZIP".</li>
 <li>Allez sur la page <a href="https://github.com/gykhamine/Boutique_erp"><b>Boutique_erp</b></a></li>
 <li>Cliquez sur le bouton vert "Code", puis "Download ZIP".</li>
 <li>Décompressez le fichier ZIP dans votre dossier personnel.</li>
 <li>Ouvrez votre terminal, tapez <code>cd </code> (avec un espace après cd), puis glissez-déposez le dossier décompressé dans le terminal. Appuyez sur Entrée.</li>
 </ol>
<h3>Étape B : Lancer la machine</h3>
Une fois que vous êtes dans le dossier du projet (votre terminal doit afficher quelque chose qui se termine par <code>./Gykhamine $</code>), tapez simplement :
<code>python gya.py</code>
<i>Note : Le nom du fichier principal peut varier selon les versions (gy.py ou gya.py). Vérifiez le contenu du dossier.</i>
Si tout s'est bien passé, une belle fenêtre sombre avec le logo Gykhamine apparaît. Vous êtes dedans.
Notons que nous travaillons pour rendre ce processus aussi simple que possible dans le temps.
<h2 id="4-tour-de-propriétaire-linterface-v331">4. Tour de propriétaire : l'interface v3.3.1</h2>
Quand le Studio s'ouvre, il peut impressionner. C'est normal, c'est un outil professionnel. Mais ne regardez pas tout en même temps. L'écran est divisé en quatre grandes zones. Chacune a un rôle précis. Si vous comprenez à quoi sert chaque zone, vous ne serez jamais perdu.
<table style="width:100%; border-collapse: collapse; margin-top: 15px;">
 <tr style="background-color: #f6f8fa;">
 <th style="border: 1px solid #d1d5da; padding: 10px; text-align: left;">Zone</th>
 <th style="border: 1px solid #d1d5da; padding: 10px; text-align: left;">Emplacement</th>
 <th style="border: 1px solid #d1d5da; padding: 10px; text-align: left;">Son rôle en une phrase</th>
 </tr>
 <tr>
 <td style="border: 1px solid #d1d5da; padding: 10px;"><b>L'Explorateur</b></td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">Gauche</td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">C'est l'armoire à dossiers. Il montre tous les fichiers du projet.</td>
 </tr>
 <tr>
 <td style="border: 1px solid #d1d5da; padding: 10px;"><b>L'Éditeur de Blocs</b></td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">Centre</td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">C'est votre établi. Il découpe le code en cartes lisibles pour que vous puissiez le modifier.</td>
 </tr>
 <tr>
 <td style="border: 1px solid #d1d5da; padding: 10px;"><b>Le Tableau de Bord</b></td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">Droite</td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">C'est la télécommande. Les boutons pour lancer le site, gérer la base de données, le SSH, Nginx, etc.</td>
 </tr>
 <tr>
 <td style="border: 1px solid #d1d5da; padding: 10px;"><b>Le Terminal</b></td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">Bas</td>
 <td style="border: 1px solid #d1d5da; padding: 10px;">C'est le journal de bord. Il raconte ce que le logiciel est en train de faire.</td>
 </tr>
 </table>
<br>
<h3>La barre du haut (Le cockpit)</h3>
Tout en haut, vous avez une barre avec le logo et quelques boutons essentiels :
 <ul>
 <li><b>☰</b> : Cache ou affiche le panneau de gauche (l'explorateur). Pratique si vous avez un petit écran.</li>
 <li><b>📂 Open</b> : Permet de changer de projet. Si vous téléchargez une autre capsule Gykhamine, vous cliquerez ici pour la charger.</li>
 <li><b>⚙</b> : Cache ou affiche le panneau de droite (le tableau de bord).</li>
 <li><b>🖥</b> : Cache ou affiche le terminal du bas.</li>
 <li><b>⛶</b> : Met le logiciel en plein écran.</li>
 <li><b>La roue crantée</b> : Ouvre les paramètres généraux du Studio (on y reviendra).</li>
 </ul>
<h3>Zone 1 : L'Explorateur (Panneau de Gauche)</h3>
C'est ici que vous naviguez dans les fichiers. Par défaut, le Studio masque les fichiers système inutiles (ceux qui commencent par un point) pour ne pas vous embrouiller. 
En bas de ce panneau, il y a cinq petits boutons :
 <ul>
 <li><b>📄</b> : Bascule vers la vue "Arborescence" (les dossiers et fichiers).</li>
 <li><b>🕒</b> : Bascule vers la vue "Récents" (les derniers projets ouverts).</li>
 <li><b>➕</b> : Crée un nouveau fichier vide dans le projet.</li>
 <li><b>📥</b> : Importe un fichier depuis votre ordinateur vers le projet.</li>
 <li><b>🙈</b> : Le bouton magique. Il affiche ou masque les fichiers cachés. Si vous cherchez un fichier de configuration système et ne le trouvez pas, cliquez ici.</li>
 </ul>
Quand vous cliquez sur un dossier, il s'ouvre. Quand vous cliquez sur un fichier (par exemple <i>views.py</i>), il s'ouvre dans le panneau central.
<h3>Zone 2 : L'Éditeur de Blocs (Panneau Central)</h3>
C'est le cœur du réacteur. Au lieu de vous jeter 500 lignes de code Python au visage, le Studio analyse le fichier et le découpe en "blocs" logiques. Chaque bloc est une carte visuelle.
Une carte de bloc contient :
<ul>
 <li><b>Une icône et un badge coloré</b> : Ils vous disent ce qu'est le bloc. Violet pour une fonction, bleu pour une classe, orange pour un bloc Django, etc.</li>
 <li><b>Le nom du bloc</b> : Par exemple, le nom de la fonction.</li>
 <li><b>Quatre boutons d'action sur la droite</b> :
 <ul>
 <li><b>👁 (Voir)</b> : Ouvre une grande fenêtre propre pour lire tout le contenu du bloc sans être gêné.</li>
 <li><b>✏ (Modifier)</b> : Déplie le bloc pour révéler une zone de texte. C'est ici que vous changez le code. Le Studio colore le texte pour le rendre lisible.</li>
 <li><b>⧉ (Copier)</b> : Copie le code du bloc dans votre presse-papiers.</li>
 <li><b>✕ (Supprimer)</b> : Efface le bloc. Attention, c'est radical.</li>
 </ul>
 </li>
 <li><b>🤖 (IA)</b> : Nouveau ! Permet de modifier le bloc directement via l'Intelligence Artificielle locale.</li>
 </ul>
En haut de ce panneau central, il y a une barre d'outils globale :
<ul>
 <li><b>Blocks: [Nombre]</b> : Vous dit combien de blocs contient le fichier.</li>
 <li><b>➕ Add block</b> : Ajoute un nouveau bloc vide à la fin du fichier. Le Studio vous demande le type (Fonction, Classe, Commentaire) et génère la structure technique pour vous.</li>
 <li><b>↩ Undo / ↪ Redo</b> : Annule ou rétablit vos dernières actions. C'est votre filet de sécurité.</li>
 <li><b>⬇ Expand all / ⬆ Collapse all</b> : Ouvre ou ferme tous les blocs d'un coup.</li>
 <li><b>▶ Run</b> : Exécute le fichier actuel (utile pour les scripts Python autonomes).</li>
 <li><b>🎨 Edit associated CSS</b> : Si vous modifiez un fichier Python qui a un fichier de style CSS du même nom, ce bouton vous y emmène directement.</li>
 <li><b>💾 Save</b> : Le bouton le plus important. Il écrit vos modifications sur le disque dur. Pensez à cliquer dessus régulièrement.</li>
 <li><b>🛠️ Compiler C</b> : Ouvre le compilateur C/C++ intégré pour tester du code système.</li>
 </ul>
<h3>Zone 3 : Le Tableau de Bord (Panneau de Droite)</h3>
C'est ici que vous donnez des ordres à Django et à votre serveur. Oubliez les lignes de commande, tout est sous forme de boutons.
<b>Gestion des Ports</b> :
<ul>
 <li><b>🔍 Check</b> : Vérifie quels "canaux" de communication (ports) sont libres sur votre ordinateur.</li>
 <li><b>🔫 Kill port</b> : Si un vieux serveur plante et bloque le port 8000, ce bouton le force à s'arrêter.</li>
 <li><b>🔓 UFW Allow</b> : Ouvre un port dans le pare-feu Ubuntu (UFW) en un clic.</li>
 <li><b>🌐 URLs Accessibles</b> : Affiche et copie facilement les liens vers vos serveurs actifs.</li>
 </ul>
<b>Django Server</b> :
<ul>
 <li><b>▶ Dev Server</b> : Allume votre site web en mode test. Un point vert s'allume. Le Studio ouvre souvent le navigateur tout seul.</li>
 <li><b>▶ Gunicorn</b> : Allume le serveur en mode "production" (pour tester comment le site se comportera sur un vrai serveur web). Supporte désormais le SSL.</li>
 </ul>
<b>Django Commands</b> :
C'est une grille de boutons pour gérer la mémoire du site (la base de données).
<ul>
 <li><b>📐 makemigrations</b> : Dit à Django "J'ai changé la structure des données, prépare un plan de mise à jour".</li>
 <li><b>⬆ migrate</b> : Dit à Django "Applique le plan et modifie la base de données".</li>
 <li><b>👤 superuser</b> : Crée le compte administrateur tout-puissant pour accéder au panneau d'administration du site (avec interface graphique pour saisir les infos).</li>
 <li><b>📦 collectstatic</b> : Rassemble tous les fichiers de design (images, CSS) au même endroit.</li>
 <li><b>✅ check</b> : Vérifie s'il y a des erreurs de configuration dans le projet.</li>
 <li><b>🧹 flush</b> : Efface TOUTES les données de la base de données. À n'utiliser que si vous voulez repartir à zéro.</li>
 </ul>
<b>Base de données Avancée</b> :
<ul>
 <li><b>📊 Visualiser les Tables</b> : Affiche le contenu réel de votre base de données dans un tableau interactif, avec export CSV/Excel.</li>
 <li><b>🐘 PostgreSQL</b> : Boutons pour Initialiser, Créer DB, Démarrer et Arrêter PostgreSQL directement depuis l'interface.</li>
 <li><b>🔴 Redis</b> : Démarrage et arrêt simplifiés de Redis pour le cache.</li>
 </ul>
<b>Sécurité & Réseau (SSL/Nginx)</b> :
<ul>
 <li><b>🔑 Générer Certificat SSL</b> : Crée automatiquement un certificat auto-signé pour activer le HTTPS sur Gunicorn et Nginx.</li>
 <li><b>🌐 Nginx</b> : Configuration, Démarrage, Arrêt et Redémarrage de Nginx. Inclut un éditeur visuel pour modifier la configuration Nginx sans toucher aux fichiers textes.</li>
 </ul>
<b>DevOps & Systèmes</b> :
<ul>
 <li><b>📁 NFS</b> : Configurez et montez des partages réseau NFS (Serveur et Client) en un clic.</li>
 <li><b>🔐 SSH</b> : Lancez un serveur SSH local ou connectez-vous à distance via un terminal TTY natif intégré.</li>
 <li><b>🐍 Venv</b> : Créez, activez (dans un terminal TTY) et supprimez des environnements virtuels Python.</li>
 </ul>
<b>Autres outils</b> :
<ul>
 <li><b>💊 Gykhamine Capsule</b> : Des raccourcis pour lancer des scripts spécifiques au projet GCI.</li>
 <li><b>🤖 AI (llama.cpp)</b> : Permet de configurer et lancer une intelligence artificielle locale pour vous aider à coder.</li>
 <li><b>📦 ZIP Archiving</b> : Compresse tout votre projet en un fichier ZIP propre (en ignorant les fichiers inutiles), ou décompresse une sauvegarde.</li>
 <li><b>⏹ Stop all</b> : Le bouton d'urgence. Arrête tous les serveurs lancés par le Studio.</li>
 </ul>
<h3>Zone 4 : Le Terminal (Panneau du Bas)</h3>
C'est la mémoire du logiciel. Quand vous cliquez sur un bouton du tableau de bord, c'est ici que s'affiche le résultat. 
Si vous voyez <i>✅ Finished (code 0)</i>, c'est que tout s'est bien passé. Le code 0 est le code universel pour "Succès".
Si vous voyez des textes en rouge ou des erreurs, c'est ici qu'il faut lire pour comprendre pourquoi ça a bloqué.
En bas à droite de ce panneau, il y a un champ de texte avec une invite <code>➜</code>. Vous pouvez y taper des commandes manuellement si vous savez ce que vous faites, mais ce n'est pas obligatoire.
<b>Nouveautés Terminal :</b>
<ul>
 <li><b>🔍 Analyseur Logs IA</b> : Collez des logs d'erreur et l'IA vous explique le problème et la solution.</li>
 <li><b>🤖 Générateur Cmd IA</b> : Décrivez une action en français (ex: "supprimer tous les fichiers tmp") et l'IA génère la commande Linux exacte.</li>
</ul>
<h2 id="5-comprendre-django-sans-être-ingénieur">5. Comprendre Django sans être ingénieur</h2>
Pour utiliser le Studio sur le projet Boutique ERP, il faut comprendre minimalement comment Django est rangé. Imaginez que votre projet est un restaurant.
<ul>
 <li><b>models.py</b> : C'est le inventaire. Il définit ce qu'est un "Client", ce qu'est un "Produit", ce qu'est une "Commande". C'est la structure de votre base de données.</li>
 <li><b>views.py</b> : C'est la cuisine. C'est là que se trouve la logique. Quand un client demande à voir ses commandes, c'est une "vue" qui va chercher l'information dans l'inventaire et prépare l'assiette.</li>
 <li><b>templates/ (fichiers .html)</b> : C'est la salle du restaurant, la décoration. C'est ce que le client voit réellement sur son écran. Le Studio découpe ces fichiers en blocs Django pour que vous puissiez modifier le texte et la mise en page facilement.</li>
 <li><b>static/ (fichiers .css, .js, images)</b> : C'est l'ambiance lumineuse, la musique, les couleurs. Les fichiers CSS disent "ce bouton doit être rouge et rond".</li>
 <li><b>settings.py</b> : C'est le bureau du directeur. On y configure les accès à la base de données, le nom du restaurant, les règles de sécurité. Ne modifiez ce fichier que si vous savez exactement ce que vous faites.</li>
 </ul>
<h2 id="6-outils-devops-et-infrastructure-intégrés">6. Outils DevOps et Infrastructure Intégrés</h2>
La version 3.3.1 transforme Gykhamine Studio en un outil de déploiement complet.
<h3>PostgreSQL & Redis</h3>
Au lieu d'installer et configurer ces bases de données manuellement via le terminal, utilisez les panneaux dédiés à droite.
<ul>
 <li>Sélectionnez votre partition disque dans les Paramètres.</li>
 <li>Cliquez sur <b>Init</b> pour préparer l'espace.</li>
 <li>Cliquez sur <b>Créer DB</b> pour générer l'utilisateur et la base.</li>
 <li>Cliquez sur <b>Démarrer</b> pour lancer le service.</li>
</ul>
<h3>Nginx & SSL</h3>
Pour mettre votre site en production sécurisée (HTTPS) :
<ol>
 <li>Allez dans la section <b>SSL / HTTPS</b> et cliquez sur <b>🔑 Générer Certificat SSL</b>.</li>
 <li>Configurez Nginx via le bouton <b>⚙ Configurer</b> (vous pouvez définir le nom de domaine, les ports, et les redirections visuellement).</li>
 <li>Cliquez sur <b>▶ Démarrer Nginx</b>.</li>
</ol>
<h3>SSH & NFS</h3>
Partagez vos fichiers médias sur le réseau local via <b>NFS Serveur</b> ou accédez à votre serveur à distance via <b>SSH Client</b> qui ouvre un vrai terminal interactif dans une fenêtre séparée.
<h2 id="7-intelligence-artificielle-locale">7. Intelligence Artificielle Locale</h2>
Gykhamine Studio intègre <b>Llama.cpp</b> pour vous assister sans envoyer vos données sur Internet.
<h3>Configuration</h3>
Cliquez sur <b>⚙️ Configurer & Lancer</b> dans la section AI. Sélectionnez le binaire <code>llama-server</code> et votre modèle <code>.gguf</code> (ex: Qwen2.5-Coder).
<h3>Fonctionnalités IA</h3>
<ul>
 <li><b>Modification de Bloc</b> : Cliquez sur 🤖 dans un bloc de code, décrivez la modification souhaitée, et l'IA réécrit le code pour vous.</li>
 <li><b>Analyseur de Logs</b> : Copiez-collez une erreur complexe, l'IA vous donne la cause et la solution.</li>
 <li><b>Générateur de Commandes</b> : Dites ce que vous voulez faire en français, l'IA vous donne la commande Linux exacte.</li>
 <li><b>Élaborateur de Processus Métier</b> : Décrivez un besoin fonctionnel (ex: "Gestion des retours produits"), l'IA génère un plan JSON détaillé des fichiers Django à modifier.</li>
</ul>
<h2 id="8-outils-systeme-et-developpement">8. Outils Système et Développement (C/C++, Git, Venv)</h2>
Le Studio ne se limite pas à Python. Il inclut des outils puissants pour le développement système et la gestion de version.
<h3>🛠️ Compilateur C/C++ Intégré</h3>
Accessible via le bouton <b>🛠️ Compiler C</b> dans la barre d'outils de l'éditeur.
<ul>
 <li><b>Compilation Multi-format</b> : Compilez votre code en exécutable (.out), bibliothèque partagée (.so) ou module kernel (.ko).</li>
 <li><b>Détection Automatique</b> : Détecte automatiquement si vous écrivez du C ou du C++ et utilise le bon compilateur (gcc ou g++).</li>
 <li><b>Optimisation IA (Eigen3)</b> : Demandez à l'IA d'optimiser votre code C++ pour les performances numériques.</li>
</ul>
<h3>🐙 Mini GitHub Desktop</h3>
Accessible via le bouton <b>🐙 Mini GitHub Desktop</b> dans le panneau de droite.
<ul>
 <li><b>Clonage Simplifié</b> : Clonez n'importe quel dépôt Git en entrant l'URL et le chemin local.</li>
 <li><b>Gestion des Modifications</b> : Faites un "Add All" et un "Commit & Push" avec une interface graphique simple.</li>
 <li><b>Historique Visuel</b> : Suivez les sorties Git directement dans la fenêtre.</li>
</ul>
<h3>🐍 Environnements Virtuels (Venv)</h3>
Gérez vos dépendances Python isolées sans quitter le Studio.
<ul>
 <li><b>Create</b> : Crée un environnement virtuel nommé "venv" à la racine du projet.</li>
 <li><b>Install Pkg</b> : Installe des paquets Pip (ex: pandas, requests) directement dans le venv actif via un terminal TTY.</li>
 <li><b>Activate Shell</b> : Ouvre un terminal TTY avec le venv déjà activé.</li>
</ul>
<h2 id="9-scénarios-pratiques-de-la-vie-réelle">9. Scénarios pratiques de la vie réelle</h2>
La théorie c'est bien, la pratique c'est mieux. Voici comment vous allez travailler au quotidien.
<h3>Scénario 1 : Changer le texte de la page d'accueil de la boutique</h3>
 <ol>
 <li>Dans le panneau de gauche, ouvrez le dossier <i>templates</i>.</li>
 <li>Cherchez le fichier qui s'appelle <i>home.html</i> ou <i>index.html</i> et cliquez dessus.</li>
 <li>Au centre, le Studio a découpé la page en blocs. Repérez un bloc de type "Template" ou "Django Block" qui contient le texte d'accueil.</li>
 <li>Cliquez sur le crayon <b>✏</b> de ce bloc.</li>
 <li>Modifiez le texte dans la zone qui s'est ouverte (par exemple, changez "Bienvenue" en "Bienvenue à la Boutique GCI").</li>
 <li>Cliquez sur le petit bouton vert <b>💾 Save</b> à l'intérieur du bloc.</li>
 <li>Ensuite, cliquez sur le gros bouton <b>💾 Save</b> tout en haut de la barre d'outils centrale pour valider dans le fichier.</li>
 <li>Si votre serveur de développement est allumé (point vert dans le panneau de droite), rafraîchissez simplement votre navigateur web. Le changement est live.</li>
 </ol>
<h3>Scénario 2 : Ajouter un nouveau champ dans la base de données (ex: "Numéro de téléphone" pour les clients)</h3>
 <ol>
 <li>Dans le panneau de gauche, cliquez sur le fichier <i>models.py</i>.</li>
 <li>Au centre, trouvez le bloc qui s'appelle "Client" (c'est une classe, badge bleu).</li>
 <li>Cliquez sur le crayon <b>✏</b> pour le modifier.</li>
 <li>À la fin de la liste des champs, ajoutez une ligne : <code>telephone = models.CharField(max_length=20, blank=True, null=True)</code>. (Oui, ici il faut taper un peu de code, mais le Studio vous empêche de casser le reste du fichier).</li>
 <li>Sauvegardez le bloc, puis sauvegardez le fichier global.</li>
 <li>Maintenant, il faut dire à Django de mettre à jour la base de données. Dans le panneau de droite, cliquez sur <b>📐 makemigrations</b>. Regardez le terminal en bas, il doit dire "OK".</li>
 <li>Ensuite, cliquez sur <b>⬆ migrate</b>. Le terminal confirme que la colonne "telephone" a été créée dans la base de données.</li>
 <li>C'est fini. Votre boutique connaît maintenant les numéros de téléphone.</li>
 </ol>
<h3>Scénario 3 : Mettre le site en HTTPS (SSL)</h3>
 <ol>
 <li>Dans le panneau de droite, section <b>SSL / HTTPS</b>, cliquez sur <b>🔑 Générer Certificat SSL</b>.</li>
 <li>Attendez que le terminal confirme la génération des fichiers <code>cert.pem</code> et <code>key.pem</code>.</li>
 <li>Le SSL s'active automatiquement dans la configuration.</li>
 <li>Redémarrez Gunicorn ou Nginx via leurs boutons respectifs.</li>
 <li>Votre site est maintenant accessible en https:// (note : comme le certificat est auto-signé, le navigateur affichera une alerte de sécurité, c'est normal pour un test local).</li>
 </ol>
<h2 id="10-glossaire-de-survie">10. Glossaire de survie</h2>
Pour finir, voici les termes techniques que vous allez croiser, traduits en français courant.
<ul>
 <li><b>Capsule Gykhamine</b> : Le nom qu'on donne à nos projets Django pré-emballés et configurés pour être utilisés avec ce Studio.</li>
 <li><b>Base de données</b> : Le grand tableau Excel invisible où sont stockés tous les clients, les produits, les commandes. Django s'occupe de lire et écrire dedans pour vous.</li>
 <li><b>Migration</b> : L'action de modifier la structure de la base de données. Si vous ajoutez un champ "Téléphone", Django doit "migrer" la base pour créer physiquement cette nouvelle colonne.</li>
 <li><b>Localhost / 127.0.0.1</b> : C'est l'adresse de votre propre ordinateur. Quand le Studio dit que le site est sur <i>localhost:8000</i>, ça veut dire que le site n'existe que sur votre machine. Personne d'autre sur Internet ne peut le voir.</li>
 <li><b>Port</b> : Une porte virtuelle sur votre ordinateur. Le serveur web entre par la porte 8000. Si la porte est bloquée par un autre programme, le site ne peut pas sortir.</li>
 <li><b>Requête (Query)</b> : Une question posée à la base de données. "Donne-moi tous les clients qui s'appellent Jean".</li>
 <li><b>Template</b> : Un modèle de page web. C'est un fichier HTML avec des trous dedans. Django remplit les trous avec les vraies données de la base de données au moment où l'utilisateur demande la page.</li>
 <li><b>WSL</b> : Windows Subsystem for Linux. L'outil de Microsoft qui permet de faire tourner Linux dans Windows.</li>
 <li><b>TTY Native</b> : Un terminal complet qui s'ouvre dans une fenêtre séparée, permettant d'utiliser des commandes interactives comme <code>top</code>, <code>nano</code> ou <code>ssh</code> correctement.</li>
 </ul>
<br>
<div style="background-color: #e6f3ff; padding: 20px; border-radius: 10px; border-left: 5px solid #007acc; margin-top: 30px;">
 <h3 style="margin-top: 0;">Un dernier mot</h3>
 <p>Le développement logiciel n'est pas de la magie noire. C'est juste de la logique et de l'organisation. Gykhamine Studio a été conçu à Brazzaville avec une conviction forte : la technologie doit être un outil d'émancipation, pas une barrière élitiste. </p>
 <p>Explorez, cliquez, testez. Vous ne pouvez pas casser votre ordinateur avec ce logiciel. Le pire qui puisse arriver, c'est que vous deviez re-télécharger le projet Boutique ERP et recommencer. Alors n'ayez pas peur de manipuler les blocs, de changer les couleurs, de tordre le code dans tous les sens. C'est comme ça qu'on apprend.</p>
 <p>Si vous bloquez sur un problème très spécifique, n'hésitez pas à ouvrir une "Issue" sur le dépôt GitHub du projet. Expliquez ce que vous essayiez de faire, et copiez-collez le message du terminal. La communauté et l'équipe du GCI sont là pour vous dépanner.</p>
 <p><i>Bon courage, et bon code (visuel) !</i></p>
 </div>
