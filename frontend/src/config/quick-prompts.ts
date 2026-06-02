import {
  BookOpen,
  Lightbulb,
  Mic2,
  Megaphone,
  Newspaper,
  Youtube,
  type LucideIcon,
} from "lucide-react"

/**
 * Centralized Quick Prompts configuration.
 *
 * Structure: language → category → content
 *   quickPrompts["english"]["narrate-story"]
 *
 * Adding a language or category here automatically flows through the UI
 * without touching any component. Category display metadata (label + icon)
 * lives in QUICK_PROMPT_CATEGORIES; the per-language copy lives in quickPrompts.
 *
 * All non-English copy is written natively (not machine-translated) so each
 * sample reads naturally for TTS demonstrations in its own language.
 */

export type QuickPromptCategory =
  | "narrate-story"
  | "explain-concept"
  | "podcast-intro"
  | "advertisement"
  | "news-report"
  | "youtube-narration"

export type QuickPromptLanguage =
  | "english"
  | "portuguese"
  | "spanish"
  | "french"
  | "german"
  | "chinese"
  | "japanese"

export interface QuickPromptCategoryMeta {
  id: QuickPromptCategory
  label: string
  icon: LucideIcon
}

export const QUICK_PROMPT_CATEGORIES: QuickPromptCategoryMeta[] = [
  { id: "narrate-story", label: "Narrate a story", icon: BookOpen },
  { id: "explain-concept", label: "Explain a concept", icon: Lightbulb },
  { id: "podcast-intro", label: "Podcast introduction", icon: Mic2 },
  { id: "advertisement", label: "Advertisement", icon: Megaphone },
  { id: "news-report", label: "News report", icon: Newspaper },
  { id: "youtube-narration", label: "YouTube narration", icon: Youtube },
]

export const quickPrompts: Record<
  QuickPromptLanguage,
  Record<QuickPromptCategory, string>
> = {
  english: {
    "narrate-story":
      "In a small coastal town, an old lighthouse stood watch over the sea for more than a century. Most people passed by without paying much attention to it, but a young engineer named Ethan became fascinated by its history. Every evening after work, he would climb the narrow staircase and listen to the sound of the waves crashing below.\n\nOne stormy night, while exploring the upper chamber, Ethan discovered a hidden notebook tucked behind a wooden panel. Inside were stories written by former lighthouse keepers, describing ship rescues, mysterious signals, and moments of courage during violent storms. What started as simple curiosity soon became a journey through generations of forgotten memories.",
    "explain-concept":
      "Artificial intelligence is a field of computer science focused on creating systems that can perform tasks normally requiring human intelligence. These tasks include recognizing speech, understanding language, identifying patterns, and making decisions based on data.\n\nModern AI systems learn from examples instead of following only fixed instructions. By processing large amounts of information, they can discover relationships and improve their performance over time. This ability to learn makes AI useful in healthcare, education, transportation, software development, and many other industries.",
    "podcast-intro":
      "Welcome to today's episode. In this podcast, we explore the intersection of technology, creativity, and entrepreneurship. Every week, we invite experts, builders, and innovators to share the lessons they've learned while creating products and solving real-world problems.\n\nWhether you're a developer, founder, designer, or simply curious about emerging technologies, you'll find practical insights and inspiring stories that can help you grow. Let's get started.",
    advertisement:
      "Imagine having access to professional-quality voice generation directly from your computer. No expensive subscriptions, no complicated setup, and complete control over your content.\n\nOmniVoice allows you to generate realistic speech, clone voices, and create high-quality audio in multiple languages. Whether you're creating videos, podcasts, audiobooks, or educational content, OmniVoice helps transform ideas into engaging audio experiences.",
    "news-report":
      "Good evening. Today's top story highlights significant advances in artificial intelligence and speech technology. Several open-source projects have introduced new models capable of generating highly realistic voices while requiring fewer computing resources than previous generations.\n\nIndustry experts believe these developments could increase accessibility and reduce costs for creators, educators, and businesses around the world. More updates will follow as the technology continues to evolve.",
    "youtube-narration":
      "Have you ever wondered how modern voice cloning works? In this video, we'll break down the technology behind synthetic speech and explain how AI models learn the characteristics of a person's voice.\n\nWe'll also look at practical applications, ethical considerations, and the tools available today. By the end of the video, you'll have a clear understanding of how these systems operate and where the industry is heading next.",
  },
  portuguese: {
    "narrate-story":
      "Em uma pequena cidade litorânea, um antigo farol observava o oceano há mais de cem anos. Enquanto a maioria das pessoas passava por ele sem notar sua importância, um jovem engenheiro chamado Lucas desenvolveu uma curiosidade incomum por sua história. Todas as tardes, após o trabalho, ele subia os degraus estreitos e observava o horizonte.\n\nDurante uma noite de tempestade, Lucas encontrou um caderno escondido atrás de uma parede de madeira. As páginas continham relatos de antigos guardiões do farol, descrevendo resgates, tempestades e histórias de coragem. O que começou como uma simples investigação transformou-se em uma jornada por memórias esquecidas.",
    "explain-concept":
      "A inteligência artificial é uma área da computação dedicada ao desenvolvimento de sistemas capazes de executar tarefas normalmente associadas à inteligência humana. Entre essas tarefas estão o reconhecimento de fala, a interpretação de linguagem, a identificação de padrões e a tomada de decisões.\n\nOs modelos modernos aprendem analisando grandes volumes de dados. Em vez de seguir apenas regras fixas, eles conseguem identificar relações e melhorar seu desempenho ao longo do tempo. Essa capacidade permite aplicações em saúde, educação, transporte, pesquisa e desenvolvimento de software.",
    "podcast-intro":
      "Seja muito bem-vindo a mais um episódio do nosso podcast. Aqui discutimos tecnologia, inovação, inteligência artificial e os desafios enfrentados por profissionais que constroem produtos digitais no mundo moderno.\n\nA cada episódio, compartilhamos experiências, aprendizados e conversas com pessoas que estão criando soluções reais para problemas complexos. Prepare-se para uma conversa interessante e cheia de insights práticos.",
    advertisement:
      "Imagine poder criar narrações profissionais, clonar vozes e produzir áudio de alta qualidade diretamente do seu computador. Sem depender de serviços caros ou processos complicados.\n\nCom o OmniVoice, você tem acesso a ferramentas modernas de síntese de voz capazes de transformar textos em áudio natural em diversos idiomas. É uma solução ideal para criadores de conteúdo, empresas, professores e desenvolvedores.",
    "news-report":
      "Boa noite. Os avanços recentes em inteligência artificial continuam transformando a forma como pessoas e empresas produzem conteúdo digital. Novos modelos de voz estão tornando a síntese de fala mais acessível, eficiente e realista.\n\nEspecialistas acreditam que essas tecnologias terão impacto significativo em áreas como educação, entretenimento, acessibilidade e comunicação corporativa. Mais informações serão divulgadas ao longo dos próximos meses.",
    "youtube-narration":
      "Você já se perguntou como funciona a clonagem de voz utilizando inteligência artificial? Neste vídeo vamos explorar os princípios por trás dessa tecnologia e mostrar como os modelos aprendem a reproduzir características vocais humanas.\n\nTambém veremos exemplos práticos, limitações atuais e possíveis aplicações para criadores de conteúdo, empresas e desenvolvedores. Vamos começar.",
  },
  spanish: {
    "narrate-story":
      "En un pequeño pueblo costero, un antiguo faro vigilaba el mar desde hacía más de un siglo. La mayoría de la gente pasaba junto a él sin prestarle demasiada atención, pero un joven ingeniero llamado Mateo quedó fascinado por su historia. Cada tarde, al salir del trabajo, subía la estrecha escalera y escuchaba el sonido de las olas rompiendo abajo.\n\nUna noche de tormenta, mientras exploraba la sala superior, Mateo descubrió un cuaderno escondido detrás de un panel de madera. En sus páginas, antiguos fareros habían dejado relatos de rescates en alta mar, señales misteriosas y momentos de valentía durante feroces tempestades. Lo que comenzó como simple curiosidad pronto se convirtió en un viaje por generaciones de recuerdos olvidados.",
    "explain-concept":
      "La inteligencia artificial es un campo de la informática dedicado a crear sistemas capaces de realizar tareas que normalmente requieren inteligencia humana. Entre esas tareas se encuentran reconocer el habla, comprender el lenguaje, identificar patrones y tomar decisiones a partir de los datos.\n\nLos sistemas modernos aprenden a partir de ejemplos en lugar de seguir únicamente reglas fijas. Al procesar grandes cantidades de información, son capaces de descubrir relaciones y mejorar su rendimiento con el tiempo. Esta capacidad de aprender hace que la inteligencia artificial sea útil en la salud, la educación, el transporte, el desarrollo de software y muchos otros sectores.",
    "podcast-intro":
      "Te damos la bienvenida a un nuevo episodio. En este pódcast exploramos el punto de encuentro entre la tecnología, la creatividad y el emprendimiento. Cada semana invitamos a expertos, creadores e innovadores para que compartan las lecciones que han aprendido al desarrollar productos y resolver problemas reales.\n\nYa seas desarrollador, fundador, diseñador o simplemente sientas curiosidad por las nuevas tecnologías, aquí encontrarás ideas prácticas e historias inspiradoras que pueden ayudarte a crecer. Comencemos.",
    advertisement:
      "Imagina tener acceso a generación de voz de calidad profesional directamente desde tu ordenador. Sin suscripciones costosas, sin configuraciones complicadas y con control total sobre tu contenido.\n\nOmniVoice te permite generar voces realistas, clonar voces y crear audio de alta calidad en varios idiomas. Ya sea que produzcas vídeos, pódcasts, audiolibros o material educativo, OmniVoice te ayuda a transformar tus ideas en experiencias de audio cautivadoras.",
    "news-report":
      "Buenas noches. La noticia más destacada de hoy son los importantes avances en inteligencia artificial y tecnología del habla. Varios proyectos de código abierto han presentado nuevos modelos capaces de generar voces sumamente realistas utilizando muchos menos recursos de cómputo que las generaciones anteriores.\n\nLos expertos del sector creen que estos avances podrían mejorar la accesibilidad y reducir los costes para creadores, docentes y empresas de todo el mundo. Seguiremos informando a medida que la tecnología continúe evolucionando.",
    "youtube-narration":
      "¿Alguna vez te has preguntado cómo funciona la clonación de voz moderna? En este vídeo vamos a desglosar la tecnología detrás del habla sintética y a explicar cómo los modelos de inteligencia artificial aprenden las características de la voz de una persona.\n\nTambién veremos aplicaciones prácticas, consideraciones éticas y las herramientas disponibles hoy en día. Al final del vídeo tendrás una idea clara de cómo funcionan estos sistemas y hacia dónde se dirige la industria.",
  },
  french: {
    "narrate-story":
      "Dans une petite ville côtière, un vieux phare veillait sur la mer depuis plus d'un siècle. La plupart des gens passaient devant sans vraiment y prêter attention, mais un jeune ingénieur nommé Antoine se passionna pour son histoire. Chaque soir, après le travail, il gravissait l'étroit escalier et écoutait le fracas des vagues en contrebas.\n\nUn soir de tempête, en explorant la chambre supérieure, Antoine découvrit un carnet caché derrière un panneau de bois. À l'intérieur, d'anciens gardiens avaient consigné des récits de sauvetages en mer, de signaux mystérieux et de moments de courage au cœur de violentes tempêtes. Ce qui n'était qu'une simple curiosité devint peu à peu un voyage à travers des générations de souvenirs oubliés.",
    "explain-concept":
      "L'intelligence artificielle est un domaine de l'informatique qui vise à créer des systèmes capables d'accomplir des tâches nécessitant habituellement l'intelligence humaine. Parmi ces tâches figurent la reconnaissance de la parole, la compréhension du langage, l'identification de motifs et la prise de décisions à partir de données.\n\nLes systèmes modernes apprennent à partir d'exemples plutôt que de suivre uniquement des règles figées. En traitant de grandes quantités d'informations, ils parviennent à découvrir des relations et à améliorer leurs performances au fil du temps. Cette capacité d'apprentissage rend l'intelligence artificielle utile dans la santé, l'éducation, les transports, le développement logiciel et bien d'autres secteurs.",
    "podcast-intro":
      "Bienvenue dans ce nouvel épisode. Dans ce podcast, nous explorons la rencontre entre la technologie, la créativité et l'entrepreneuriat. Chaque semaine, nous invitons des experts, des créateurs et des innovateurs à partager les leçons qu'ils ont tirées en concevant des produits et en résolvant des problèmes concrets.\n\nQue vous soyez développeur, fondateur, designer ou simplement curieux des technologies émergentes, vous y trouverez des conseils pratiques et des histoires inspirantes pour vous aider à progresser. C'est parti.",
    advertisement:
      "Imaginez avoir accès à une génération de voix de qualité professionnelle directement depuis votre ordinateur. Sans abonnement coûteux, sans installation compliquée, et avec un contrôle total sur vos contenus.\n\nOmniVoice vous permet de générer des voix réalistes, de cloner des voix et de créer de l'audio de haute qualité dans plusieurs langues. Que vous réalisiez des vidéos, des podcasts, des livres audio ou des contenus pédagogiques, OmniVoice transforme vos idées en expériences sonores captivantes.",
    "news-report":
      "Bonsoir. La principale actualité du jour met en lumière des avancées majeures dans l'intelligence artificielle et les technologies de la voix. Plusieurs projets open source ont présenté de nouveaux modèles capables de générer des voix extrêmement réalistes tout en consommant beaucoup moins de ressources que les générations précédentes.\n\nLes spécialistes du secteur estiment que ces progrès pourraient améliorer l'accessibilité et réduire les coûts pour les créateurs, les enseignants et les entreprises du monde entier. Nous vous tiendrons informés à mesure que la technologie continuera d'évoluer.",
    "youtube-narration":
      "Vous êtes-vous déjà demandé comment fonctionne le clonage de voix moderne ? Dans cette vidéo, nous allons décortiquer la technologie qui se cache derrière la parole synthétique et expliquer comment les modèles d'intelligence artificielle apprennent les caractéristiques de la voix d'une personne.\n\nNous aborderons également les applications concrètes, les enjeux éthiques et les outils disponibles aujourd'hui. À la fin de cette vidéo, vous comprendrez clairement le fonctionnement de ces systèmes et la direction que prend le secteur.",
  },
  german: {
    "narrate-story":
      "In einer kleinen Küstenstadt wachte ein alter Leuchtturm seit über einem Jahrhundert über das Meer. Die meisten Menschen gingen achtlos an ihm vorbei, doch ein junger Ingenieur namens Jonas war von seiner Geschichte fasziniert. Jeden Abend nach der Arbeit stieg er die schmale Treppe hinauf und lauschte dem Rauschen der Wellen, die unten gegen die Felsen schlugen.\n\nIn einer stürmischen Nacht entdeckte Jonas beim Erkunden der oberen Kammer ein verstecktes Notizbuch hinter einer Holzverkleidung. Darin hatten frühere Leuchtturmwärter ihre Geschichten festgehalten: von Schiffsrettungen, geheimnisvollen Signalen und mutigen Augenblicken inmitten heftiger Stürme. Was als bloße Neugier begann, wurde bald zu einer Reise durch Generationen vergessener Erinnerungen.",
    "explain-concept":
      "Künstliche Intelligenz ist ein Teilgebiet der Informatik, das sich darauf konzentriert, Systeme zu entwickeln, die Aufgaben übernehmen können, für die normalerweise menschliche Intelligenz nötig ist. Dazu gehören das Erkennen von Sprache, das Verstehen von Texten, das Erkennen von Mustern und das Treffen von Entscheidungen auf Grundlage von Daten.\n\nModerne KI-Systeme lernen aus Beispielen, statt nur festen Regeln zu folgen. Indem sie große Mengen an Informationen verarbeiten, erkennen sie Zusammenhänge und verbessern mit der Zeit ihre Leistung. Diese Lernfähigkeit macht künstliche Intelligenz in der Medizin, der Bildung, dem Verkehr, der Softwareentwicklung und vielen weiteren Bereichen wertvoll.",
    "podcast-intro":
      "Herzlich willkommen zur heutigen Folge. In diesem Podcast erkunden wir das Zusammenspiel von Technologie, Kreativität und Unternehmertum. Jede Woche laden wir Expertinnen, Gründer und Vordenker ein, die ihre Erfahrungen beim Entwickeln von Produkten und beim Lösen echter Probleme mit uns teilen.\n\nEgal, ob du Entwicklerin, Gründer, Designer oder einfach neugierig auf neue Technologien bist – hier findest du praktische Einblicke und inspirierende Geschichten, die dich weiterbringen. Lass uns loslegen.",
    advertisement:
      "Stell dir vor, du hättest professionelle Sprachgenerierung direkt auf deinem eigenen Computer. Ohne teure Abonnements, ohne komplizierte Einrichtung und mit voller Kontrolle über deine Inhalte.\n\nMit OmniVoice erzeugst du realistische Stimmen, klonst Stimmen und erstellst hochwertige Audioaufnahmen in mehreren Sprachen. Ob für Videos, Podcasts, Hörbücher oder Lerninhalte – OmniVoice verwandelt deine Ideen in fesselnde Klangerlebnisse.",
    "news-report":
      "Guten Abend. Die wichtigste Meldung des Tages betrifft bedeutende Fortschritte in der künstlichen Intelligenz und der Sprachtechnologie. Mehrere Open-Source-Projekte haben neue Modelle vorgestellt, die äußerst realistische Stimmen erzeugen und dabei deutlich weniger Rechenleistung benötigen als frühere Generationen.\n\nFachleute gehen davon aus, dass diese Entwicklungen die Zugänglichkeit verbessern und die Kosten für Kreative, Lehrende und Unternehmen weltweit senken könnten. Wir berichten weiter, sobald sich die Technologie weiterentwickelt.",
    "youtube-narration":
      "Hast du dich schon einmal gefragt, wie modernes Stimmklonen eigentlich funktioniert? In diesem Video erklären wir die Technologie hinter synthetischer Sprache und zeigen, wie KI-Modelle die charakteristischen Merkmale einer Stimme erlernen.\n\nAußerdem werfen wir einen Blick auf praktische Anwendungen, ethische Fragen und die heute verfügbaren Werkzeuge. Am Ende des Videos wirst du genau verstehen, wie diese Systeme arbeiten und wohin sich die Branche entwickelt.",
  },
  chinese: {
    "narrate-story":
      "在一座海边小镇上，有一座古老的灯塔，已经默默守望大海一百多年了。大多数人从它身边匆匆走过，几乎不会多看一眼，但一位名叫陈宇的年轻工程师却被它的历史深深吸引。每天下班后的傍晚，他都会沿着狭窄的楼梯一级一级地往上爬，静静聆听脚下海浪拍打礁石的声音。\n\n在一个风雨交加的夜晚，陈宇在探索灯塔顶层时，意外发现了一本藏在木板后面的笔记本。里面记录着历代守塔人留下的故事，有惊心动魄的海上营救，有神秘莫测的灯光信号，也有他们在狂风暴雨中坚守岗位的勇敢瞬间。原本只是出于好奇，没想到却变成了一段穿越几代人记忆的旅程。",
    "explain-concept":
      "人工智能是计算机科学的一个分支，专注于创造能够完成那些通常需要人类智慧才能完成的任务的系统。这些任务包括识别语音、理解语言、发现规律，以及根据数据做出判断和决策。\n\n与只会遵循固定指令的程序不同，现代人工智能系统是通过大量的例子来学习的。在处理海量信息的过程中，它们能够发现事物之间的内在联系，并随着时间不断提升自身的表现。正是这种学习能力，让人工智能在医疗、教育、交通、软件开发等众多领域都发挥着越来越重要的作用。",
    "podcast-intro":
      "欢迎收听本期节目。在这档播客里，我们一起探讨技术、创意与创业之间的交汇点。每一周，我们都会邀请不同领域的专家、创造者和创新者，与大家分享他们在打造产品、解决实际问题过程中收获的宝贵经验。\n\n无论你是开发者、创业者、设计师，还是单纯对前沿科技充满好奇，都能在这里找到实用的见解和鼓舞人心的故事，帮助你不断成长。好的，让我们正式开始吧。",
    advertisement:
      "想象一下，只需一台电脑，你就能拥有专业级别的语音生成能力。不需要昂贵的订阅费用，不需要繁琐的安装设置，而且你可以完全掌控自己的全部内容。\n\nOmniVoice 让你轻松生成逼真的语音、克隆各种声音，并制作多种语言的高质量音频。无论你是在创作视频、播客、有声书，还是制作教学内容，OmniVoice 都能帮你把脑海中的创意，变成打动人心的声音作品。",
    "news-report":
      "晚上好。今天的头条新闻聚焦于人工智能与语音技术领域取得的重大进展。多个开源项目相继推出了全新的模型，它们能够生成高度逼真的语音，同时所需的计算资源也远远低于上一代产品。\n\n业内专家普遍认为，这些进展有望提升技术的可及性，并为世界各地的创作者、教育工作者和企业大幅降低成本。随着技术的持续演进，我们也将带来更多后续报道。",
    "youtube-narration":
      "你有没有想过，如今的声音克隆技术到底是怎么实现的呢？在这期视频里，我们将带你深入了解合成语音背后的技术原理，看看人工智能模型是如何一步步学会一个人声音的独特特征的。\n\n我们还会聊一聊它在现实中的实际应用、需要注意的伦理问题，以及目前已经可以使用的各种工具。看完这期视频，相信你会对这些系统的运作方式，以及整个行业未来的发展方向，有一个清晰的认识。",
  },
  japanese: {
    "narrate-story":
      "海辺の小さな町に、百年以上ものあいだ静かに海を見守りつづけてきた古い灯台がありました。ほとんどの人は気にも留めずに通り過ぎていきましたが、ハルトという名の若い技師だけは、その歴史にすっかり心を奪われていました。彼は仕事を終えるたびに、夕暮れの細い階段をのぼり、眼下で砕ける波の音にじっと耳を傾けるのでした。\n\n嵐の夜、灯台の最上階を探っていたハルトは、木の板の裏に隠された一冊の手帳を見つけました。そこには、かつての灯台守たちが書き残した物語が綴られていました。海での救助、謎めいた光の信号、そして激しい嵐の中で見せた勇気の数々。ほんの好奇心から始まったはずの探索は、いつしか幾世代もの忘れられた記憶をたどる旅へと変わっていったのです。",
    "explain-concept":
      "人工知能とは、本来であれば人間の知能を必要とするような作業を、コンピューターに行わせることを目指す研究分野です。具体的には、音声を認識すること、言葉の意味を理解すること、パターンを見つけ出すこと、そしてデータにもとづいて判断を下すことなどが含まれます。\n\n現代の人工知能は、決められた命令にただ従うのではなく、たくさんの例から学習していくという点に大きな特徴があります。膨大な情報を処理する中で、物事どうしの関係性を見つけ出し、時間とともにその性能を高めていくのです。こうした「学ぶ力」のおかげで、人工知能は医療や教育、交通、ソフトウェア開発など、実にさまざまな分野で役立てられています。",
    "podcast-intro":
      "本日のエピソードへようこそ。このポッドキャストでは、テクノロジーと創造性、そして起業という三つの世界が交わる場所をテーマに、さまざまなお話をお届けしています。毎週、各分野の専門家やものづくりに挑む方々、革新を生み出す方々をお招きし、製品開発や現実の課題と向き合う中で得た学びを語っていただきます。\n\nエンジニアの方も、起業家やデザイナーの方も、あるいは最新の技術にただ興味があるという方も、きっとここで役立つヒントや心を動かす物語に出会えるはずです。それでは、さっそく始めていきましょう。",
    advertisement:
      "プロ品質の音声生成を、あなたのパソコンから直接使えるとしたら、どうでしょうか。高額な月額料金も、面倒な初期設定もいりません。しかも、作り出すコンテンツはすべて自分の手の中にあります。\n\nOmniVoice を使えば、自然でリアルな音声を生成したり、声をクローンしたり、さまざまな言語で高品質な音声を作り出したりできます。動画やポッドキャスト、オーディオブック、学習用の教材など、どんな用途であっても、OmniVoice はあなたのアイデアを心に響く「音」へと変えていきます。",
    "news-report":
      "こんばんは。本日の主要ニュースは、人工知能と音声技術の分野で見られた大きな進展についてです。複数のオープンソースプロジェクトが新たなモデルを発表しました。これらは従来よりもはるかに少ない計算資源で、きわめて自然でリアルな音声を生成できるとされています。\n\n専門家は、こうした進歩によって技術がより身近なものとなり、世界中のクリエイターや教育者、企業にとっての負担が軽くなる可能性があると指摘しています。技術の進化に合わせて、続報を随時お伝えしてまいります。",
    "youtube-narration":
      "最近の音声クローン技術が、いったいどのような仕組みで動いているのか、気になったことはありませんか。この動画では、合成音声を支える技術をわかりやすく解き明かしながら、人工知能のモデルが人の声の特徴をどのように学んでいくのかを丁寧に説明していきます。\n\nさらに、実際の活用例や、知っておきたい倫理的な課題、そして今すぐ使えるツールについても紹介します。最後まで見ていただければ、これらの仕組みがどう動いているのか、そして業界がこれからどこへ向かっていくのかが、はっきりと見えてくるはずです。",
  },
}

/**
 * Map a UI language label (as shown in the Select, e.g. "English", "Auto")
 * to a config key. Unknown languages and "Auto" fall back to English.
 */
export function resolveQuickPromptLanguage(label: string): QuickPromptLanguage {
  const key = label.trim().toLowerCase()
  if (key in quickPrompts) {
    return key as QuickPromptLanguage
  }
  return "english"
}
