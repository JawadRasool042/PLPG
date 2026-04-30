"""
Seed learning notes for each domain/interest
Each note has: interest, topic, order, summary, content (sections with text + key_points)
"""
from database import get_collection, init_db


NOTES = [

    # ═══════════════════════════════════════════════════════
    # AI/ML
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'AI/ML', 'topic': 'What is Artificial Intelligence?', 'order': 1,
        'emoji': '🤖', 'readTime': '5 min',
        'summary': 'AI is the simulation of human intelligence in machines. Learn the basics.',
        'content': [
            {
                'heading': 'Definition',
                'text': 'Artificial Intelligence (AI) refers to the simulation of human intelligence processes by computer systems. These processes include learning (acquiring information and rules), reasoning (using rules to reach conclusions), and self-correction.',
                'key_points': [
                    'AI mimics human cognitive functions',
                    'Includes learning, reasoning, and problem-solving',
                    'Powers voice assistants, recommendation systems, self-driving cars'
                ]
            },
            {
                'heading': 'Types of AI',
                'text': 'AI is broadly classified into Narrow AI (designed for specific tasks like chess or image recognition) and General AI (hypothetical AI with human-level intelligence across all domains).',
                'key_points': [
                    'Narrow AI: Siri, Google Translate, spam filters',
                    'General AI: Does not exist yet — still theoretical',
                    'Machine Learning is a subset of AI'
                ]
            },
            {
                'heading': 'Machine Learning vs AI',
                'text': 'Machine Learning is a subset of AI where systems learn from data without being explicitly programmed. Deep Learning is a subset of ML using neural networks with many layers.',
                'key_points': [
                    'AI ⊃ Machine Learning ⊃ Deep Learning',
                    'ML learns patterns from data automatically',
                    'Deep Learning uses multi-layer neural networks'
                ]
            }
        ]
    },
    {
        'interest': 'AI/ML', 'topic': 'Supervised vs Unsupervised Learning', 'order': 2,
        'emoji': '📊', 'readTime': '6 min',
        'summary': 'The two main types of machine learning — understand when to use each.',
        'content': [
            {
                'heading': 'Supervised Learning',
                'text': 'In supervised learning, the model is trained on labeled data — each input has a corresponding correct output. The model learns to map inputs to outputs.',
                'key_points': [
                    'Uses labeled training data',
                    'Examples: spam detection, house price prediction',
                    'Algorithms: Linear Regression, Decision Trees, SVM, Neural Networks'
                ]
            },
            {
                'heading': 'Unsupervised Learning',
                'text': 'In unsupervised learning, the model finds patterns in unlabeled data on its own. There are no correct answers provided during training.',
                'key_points': [
                    'No labeled data required',
                    'Examples: customer segmentation, anomaly detection',
                    'Algorithms: K-Means, DBSCAN, PCA, Autoencoders'
                ]
            },
            {
                'heading': 'Reinforcement Learning',
                'text': 'An agent learns by interacting with an environment, receiving rewards for good actions and penalties for bad ones. Used in game AI and robotics.',
                'key_points': [
                    'Agent, Environment, Reward, Action',
                    'Examples: AlphaGo, game-playing AI',
                    'Trial and error learning approach'
                ]
            }
        ]
    },
    {
        'interest': 'AI/ML', 'topic': 'Neural Networks Explained', 'order': 3,
        'emoji': '🧠', 'readTime': '7 min',
        'summary': 'How neural networks work — the building blocks of deep learning.',
        'content': [
            {
                'heading': 'What is a Neural Network?',
                'text': 'A neural network is a series of algorithms that attempt to recognize underlying relationships in data through a process that mimics the way the human brain operates.',
                'key_points': [
                    'Inspired by biological neurons',
                    'Consists of input, hidden, and output layers',
                    'Each connection has a weight that is adjusted during training'
                ]
            },
            {
                'heading': 'How Training Works',
                'text': 'Training involves forward propagation (passing data through the network to get predictions) and backpropagation (adjusting weights based on errors using gradient descent).',
                'key_points': [
                    'Forward pass: input → prediction',
                    'Loss function measures prediction error',
                    'Backpropagation updates weights to reduce error'
                ]
            },
            {
                'heading': 'Activation Functions',
                'text': 'Activation functions introduce non-linearity into the network, allowing it to learn complex patterns. Common ones include ReLU, Sigmoid, and Softmax.',
                'key_points': [
                    'ReLU: max(0, x) — most common in hidden layers',
                    'Sigmoid: outputs 0-1 — used for binary classification',
                    'Softmax: outputs probabilities — used for multi-class output'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Web Development
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Web Development', 'topic': 'HTML Fundamentals', 'order': 1,
        'emoji': '🌐', 'readTime': '5 min',
        'summary': 'HTML is the backbone of every webpage. Learn the essential tags and structure.',
        'content': [
            {
                'heading': 'What is HTML?',
                'text': 'HTML (HyperText Markup Language) is the standard language for creating web pages. It describes the structure of a web page using elements represented by tags.',
                'key_points': [
                    'HTML stands for HyperText Markup Language',
                    'Uses tags like <h1>, <p>, <div>, <a>',
                    'Every webpage starts with <!DOCTYPE html>'
                ]
            },
            {
                'heading': 'Essential HTML Tags',
                'text': 'Key tags include headings (h1-h6), paragraphs (p), links (a), images (img), lists (ul, ol, li), divs for layout, and forms for user input.',
                'key_points': [
                    '<h1> to <h6>: headings (h1 is largest)',
                    '<a href="url">: creates hyperlinks',
                    '<img src="path" alt="desc">: embeds images',
                    '<form>, <input>, <button>: user input'
                ]
            },
            {
                'heading': 'HTML Document Structure',
                'text': 'Every HTML document has a head (metadata, title, CSS links) and a body (visible content). Semantic tags like header, nav, main, footer improve accessibility.',
                'key_points': [
                    '<head>: metadata, not visible to users',
                    '<body>: all visible page content',
                    'Semantic HTML improves SEO and accessibility'
                ]
            }
        ]
    },
    {
        'interest': 'Web Development', 'topic': 'CSS Styling & Layout', 'order': 2,
        'emoji': '🎨', 'readTime': '6 min',
        'summary': 'CSS makes websites beautiful. Learn selectors, box model, and Flexbox.',
        'content': [
            {
                'heading': 'CSS Basics',
                'text': 'CSS (Cascading Style Sheets) controls the visual presentation of HTML elements. You can apply styles using selectors targeting elements, classes, or IDs.',
                'key_points': [
                    'Selector { property: value; }',
                    'Class selector: .classname',
                    'ID selector: #idname',
                    'Cascading means styles can override each other'
                ]
            },
            {
                'heading': 'The Box Model',
                'text': 'Every HTML element is a box with content, padding (space inside), border, and margin (space outside). Understanding this is key to layout.',
                'key_points': [
                    'Content → Padding → Border → Margin',
                    'box-sizing: border-box makes sizing intuitive',
                    'Use browser DevTools to inspect box model'
                ]
            },
            {
                'heading': 'Flexbox Layout',
                'text': 'Flexbox is a CSS layout model that makes it easy to align and distribute space among items in a container, even when their size is unknown.',
                'key_points': [
                    'display: flex on parent container',
                    'justify-content: aligns items horizontally',
                    'align-items: aligns items vertically',
                    'flex-wrap: allows items to wrap to next line'
                ]
            }
        ]
    },
    {
        'interest': 'Web Development', 'topic': 'JavaScript Essentials', 'order': 3,
        'emoji': '⚡', 'readTime': '8 min',
        'summary': 'JavaScript makes websites interactive. Learn variables, functions, and DOM.',
        'content': [
            {
                'heading': 'JavaScript Basics',
                'text': 'JavaScript is a programming language that runs in the browser. It can manipulate HTML/CSS, handle user events, and communicate with servers.',
                'key_points': [
                    'let and const for variable declaration',
                    'Functions: function name() {} or arrow () => {}',
                    'Arrays and Objects are core data structures'
                ]
            },
            {
                'heading': 'DOM Manipulation',
                'text': 'The DOM (Document Object Model) represents the HTML as a tree. JavaScript can select, modify, add, or remove elements dynamically.',
                'key_points': [
                    'document.getElementById("id")',
                    'document.querySelector(".class")',
                    'element.innerHTML = "new content"',
                    'element.addEventListener("click", handler)'
                ]
            },
            {
                'heading': 'Async JavaScript',
                'text': 'JavaScript handles asynchronous operations (like API calls) using callbacks, Promises, and async/await syntax to avoid blocking the main thread.',
                'key_points': [
                    'fetch() returns a Promise',
                    'async/await makes async code readable',
                    'try/catch handles errors in async functions'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Cybersecurity
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Cybersecurity', 'topic': 'Cybersecurity Fundamentals', 'order': 1,
        'emoji': '🔐', 'readTime': '5 min',
        'summary': 'Learn the core concepts of cybersecurity — CIA triad, threats, and defenses.',
        'content': [
            {
                'heading': 'The CIA Triad',
                'text': 'The foundation of cybersecurity is the CIA Triad: Confidentiality (only authorized users access data), Integrity (data is accurate and unmodified), and Availability (systems are accessible when needed).',
                'key_points': [
                    'Confidentiality: encryption, access controls',
                    'Integrity: hashing, digital signatures',
                    'Availability: backups, redundancy, DDoS protection'
                ]
            },
            {
                'heading': 'Common Threats',
                'text': 'Major cybersecurity threats include malware (viruses, ransomware, spyware), phishing attacks, SQL injection, man-in-the-middle attacks, and denial of service attacks.',
                'key_points': [
                    'Malware: software designed to harm systems',
                    'Phishing: tricking users into revealing credentials',
                    'SQL Injection: inserting malicious SQL into inputs',
                    'DDoS: overwhelming a server with traffic'
                ]
            },
            {
                'heading': 'Defense Strategies',
                'text': 'Defense in depth uses multiple security layers. Key strategies include firewalls, intrusion detection systems, encryption, regular patching, and security awareness training.',
                'key_points': [
                    'Principle of least privilege',
                    'Regular software updates and patching',
                    'Multi-factor authentication (MFA)',
                    'Security awareness training for users'
                ]
            }
        ]
    },
    {
        'interest': 'Cybersecurity', 'topic': 'Encryption & Cryptography', 'order': 2,
        'emoji': '🔑', 'readTime': '6 min',
        'summary': 'How encryption protects data — symmetric, asymmetric, and hashing.',
        'content': [
            {
                'heading': 'What is Encryption?',
                'text': 'Encryption converts readable data (plaintext) into an unreadable format (ciphertext) using an algorithm and key. Only those with the correct key can decrypt it.',
                'key_points': [
                    'Plaintext → Encryption → Ciphertext',
                    'Key determines how data is scrambled',
                    'Used in HTTPS, messaging apps, file storage'
                ]
            },
            {
                'heading': 'Symmetric vs Asymmetric',
                'text': 'Symmetric encryption uses the same key for encryption and decryption (fast, used for bulk data). Asymmetric uses a public/private key pair (slower, used for key exchange).',
                'key_points': [
                    'Symmetric: AES — same key both ways',
                    'Asymmetric: RSA — public key encrypts, private decrypts',
                    'HTTPS uses asymmetric to exchange symmetric keys'
                ]
            },
            {
                'heading': 'Hashing',
                'text': 'Hashing converts data into a fixed-length string (hash). It is one-way — you cannot reverse a hash. Used for password storage and data integrity verification.',
                'key_points': [
                    'SHA-256, bcrypt are common hash algorithms',
                    'Same input always produces same hash',
                    'Passwords stored as hashes, not plaintext',
                    'Salt added to prevent rainbow table attacks'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Data Science
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Data Science', 'topic': 'Introduction to Data Science', 'order': 1,
        'emoji': '📊', 'readTime': '5 min',
        'summary': 'What data scientists do and the tools they use.',
        'content': [
            {
                'heading': 'What is Data Science?',
                'text': 'Data Science is an interdisciplinary field that uses scientific methods, algorithms, and systems to extract knowledge and insights from structured and unstructured data.',
                'key_points': [
                    'Combines statistics, programming, and domain knowledge',
                    'Goal: extract actionable insights from data',
                    'Used in business, healthcare, finance, research'
                ]
            },
            {
                'heading': 'The Data Science Process',
                'text': 'The typical workflow: Define problem → Collect data → Clean data → Explore (EDA) → Model → Evaluate → Deploy → Monitor.',
                'key_points': [
                    'EDA: Exploratory Data Analysis',
                    '80% of time is data cleaning',
                    'Model selection depends on problem type'
                ]
            },
            {
                'heading': 'Key Tools',
                'text': 'Python is the primary language with libraries like Pandas (data manipulation), NumPy (numerical computing), Matplotlib/Seaborn (visualization), and Scikit-learn (ML).',
                'key_points': [
                    'Pandas: DataFrames for tabular data',
                    'NumPy: fast array operations',
                    'Matplotlib/Seaborn: charts and graphs',
                    'Jupyter Notebook: interactive coding environment'
                ]
            }
        ]
    },
    {
        'interest': 'Data Science', 'topic': 'Statistics for Data Science', 'order': 2,
        'emoji': '📈', 'readTime': '7 min',
        'summary': 'Essential statistics concepts every data scientist must know.',
        'content': [
            {
                'heading': 'Descriptive Statistics',
                'text': 'Descriptive statistics summarize and describe data. Key measures include mean (average), median (middle value), mode (most frequent), and standard deviation (spread).',
                'key_points': [
                    'Mean: sum / count',
                    'Median: middle value when sorted',
                    'Standard deviation: how spread out data is',
                    'Variance: standard deviation squared'
                ]
            },
            {
                'heading': 'Probability Basics',
                'text': 'Probability measures the likelihood of events. Key concepts include probability distributions (normal, binomial), conditional probability, and Bayes theorem.',
                'key_points': [
                    'Probability ranges from 0 to 1',
                    'Normal distribution: bell curve',
                    'P(A|B): probability of A given B',
                    "Bayes theorem updates beliefs with new evidence"
                ]
            },
            {
                'heading': 'Hypothesis Testing',
                'text': 'Hypothesis testing determines if results are statistically significant. The null hypothesis assumes no effect; we try to reject it using p-values and significance levels.',
                'key_points': [
                    'Null hypothesis (H0): no effect/difference',
                    'p-value < 0.05: reject null hypothesis',
                    't-test: compare means of two groups',
                    'Chi-square: test categorical variables'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Mobile Development
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Mobile Development', 'topic': 'Mobile Development Overview', 'order': 1,
        'emoji': '📱', 'readTime': '5 min',
        'summary': 'Native vs cross-platform development — choosing the right approach.',
        'content': [
            {
                'heading': 'Native vs Cross-Platform',
                'text': 'Native apps are built for a specific platform (Swift for iOS, Kotlin for Android). Cross-platform frameworks like Flutter and React Native allow one codebase for both platforms.',
                'key_points': [
                    'Native: best performance, platform-specific',
                    'Flutter: Dart language, single codebase',
                    'React Native: JavaScript, uses native components',
                    'Cross-platform saves development time'
                ]
            },
            {
                'heading': 'Flutter Basics',
                'text': 'Flutter uses widgets as building blocks. Everything is a widget — text, buttons, layouts. The widget tree defines the UI structure.',
                'key_points': [
                    'StatelessWidget: UI that does not change',
                    'StatefulWidget: UI that can change',
                    'Hot reload: see changes instantly',
                    'Material and Cupertino design systems'
                ]
            },
            {
                'heading': 'App Architecture',
                'text': 'Good mobile apps separate UI from business logic. Common patterns include MVC, MVVM, and BLoC (for Flutter). State management is crucial for complex apps.',
                'key_points': [
                    'Separate UI from business logic',
                    'State management: Provider, Riverpod, BLoC',
                    'Navigation: routes and navigation stacks',
                    'API integration with HTTP packages'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Cloud Computing
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Cloud Computing', 'topic': 'Cloud Computing Basics', 'order': 1,
        'emoji': '☁️', 'readTime': '5 min',
        'summary': 'What cloud computing is and the three main service models.',
        'content': [
            {
                'heading': 'What is Cloud Computing?',
                'text': 'Cloud computing delivers computing services (servers, storage, databases, networking, software) over the internet on a pay-as-you-go basis instead of owning physical hardware.',
                'key_points': [
                    'On-demand resources via internet',
                    'Pay only for what you use',
                    'Major providers: AWS, Azure, Google Cloud',
                    'Eliminates need for physical data centers'
                ]
            },
            {
                'heading': 'Service Models',
                'text': 'IaaS (Infrastructure as a Service) provides raw computing resources. PaaS (Platform as a Service) provides development platforms. SaaS (Software as a Service) provides ready-to-use applications.',
                'key_points': [
                    'IaaS: virtual machines, storage (AWS EC2)',
                    'PaaS: development platform (Heroku, App Engine)',
                    'SaaS: ready apps (Gmail, Salesforce, Office 365)',
                    'More abstraction = less control but easier to use'
                ]
            },
            {
                'heading': 'Key Cloud Concepts',
                'text': 'Scalability (handle more load), elasticity (auto-scale up/down), high availability (minimize downtime), and fault tolerance (continue working despite failures) are core cloud benefits.',
                'key_points': [
                    'Horizontal scaling: add more servers',
                    'Vertical scaling: upgrade server specs',
                    'Load balancer: distributes traffic',
                    'CDN: delivers content from nearest server'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Game Development
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Game Development', 'topic': 'Game Development Fundamentals', 'order': 1,
        'emoji': '🎮', 'readTime': '5 min',
        'summary': 'Core concepts of game development — game loop, physics, and engines.',
        'content': [
            {
                'heading': 'The Game Loop',
                'text': 'Every game runs a continuous loop: Process Input → Update Game State → Render Graphics. This loop runs 30-60+ times per second to create smooth gameplay.',
                'key_points': [
                    'Input: keyboard, mouse, controller events',
                    'Update: move objects, check collisions, AI',
                    'Render: draw everything to screen',
                    'FPS (frames per second) measures smoothness'
                ]
            },
            {
                'heading': 'Game Engines',
                'text': 'Game engines provide tools and frameworks for building games. Unity (C#) and Unreal Engine (C++) are industry standards. Godot (GDScript/C#) is a free open-source alternative.',
                'key_points': [
                    'Unity: best for mobile and indie games',
                    'Unreal Engine: best for AAA 3D games',
                    'Godot: free, open-source, beginner-friendly',
                    'Engines handle physics, audio, rendering'
                ]
            },
            {
                'heading': 'Game Physics',
                'text': 'Physics engines simulate real-world physics — gravity, collisions, rigid body dynamics. In Unity, Rigidbody components add physics to objects.',
                'key_points': [
                    'Colliders define object boundaries',
                    'Rigidbody adds gravity and physics forces',
                    'Trigger zones detect overlap without collision',
                    'Raycasting detects objects in a direction'
                ]
            }
        ]
    },

    # ═══════════════════════════════════════════════════════
    # Coding / Programming
    # ═══════════════════════════════════════════════════════
    {
        'interest': 'Coding', 'topic': 'Programming Fundamentals', 'order': 1,
        'emoji': '💻', 'readTime': '6 min',
        'summary': 'Core programming concepts every developer must master.',
        'content': [
            {
                'heading': 'Variables and Data Types',
                'text': 'Variables store data. Common data types include integers (whole numbers), floats (decimals), strings (text), booleans (true/false), and collections (lists, dictionaries).',
                'key_points': [
                    'int: whole numbers (1, 42, -5)',
                    'float: decimals (3.14, -0.5)',
                    'str: text ("hello", "world")',
                    'bool: True or False',
                    'list/array: ordered collection'
                ]
            },
            {
                'heading': 'Control Flow',
                'text': 'Control flow determines the order code executes. If/else statements make decisions. Loops (for, while) repeat code. Functions group reusable code.',
                'key_points': [
                    'if/elif/else: conditional execution',
                    'for loop: iterate over a sequence',
                    'while loop: repeat while condition is true',
                    'break: exit loop early',
                    'continue: skip to next iteration'
                ]
            },
            {
                'heading': 'Functions',
                'text': 'Functions are reusable blocks of code that perform a specific task. They take inputs (parameters) and return outputs. Good functions do one thing well.',
                'key_points': [
                    'def function_name(params): in Python',
                    'return statement sends back a value',
                    'DRY principle: Do Not Repeat Yourself',
                    'Parameters vs Arguments distinction'
                ]
            }
        ]
    },
    {
        'interest': 'Coding', 'topic': 'Data Structures', 'order': 2,
        'emoji': '🗂️', 'readTime': '7 min',
        'summary': 'Arrays, linked lists, stacks, queues — the building blocks of algorithms.',
        'content': [
            {
                'heading': 'Arrays and Lists',
                'text': 'Arrays store elements in contiguous memory with O(1) access by index. Dynamic arrays (Python lists) can grow/shrink. Best for random access and iteration.',
                'key_points': [
                    'O(1) access by index',
                    'O(n) search for unsorted array',
                    'O(1) append to end (amortized)',
                    'O(n) insert/delete in middle'
                ]
            },
            {
                'heading': 'Stacks and Queues',
                'text': 'Stack: Last In First Out (LIFO) — like a stack of plates. Queue: First In First Out (FIFO) — like a line. Both are used extensively in algorithms.',
                'key_points': [
                    'Stack: push (add), pop (remove top)',
                    'Queue: enqueue (add), dequeue (remove front)',
                    'Stack used in: undo operations, call stack',
                    'Queue used in: BFS, task scheduling'
                ]
            },
            {
                'heading': 'Hash Tables',
                'text': 'Hash tables (dictionaries in Python) store key-value pairs with O(1) average lookup. A hash function maps keys to array indices.',
                'key_points': [
                    'O(1) average lookup, insert, delete',
                    'Python dict is a hash table',
                    'Collision: two keys map to same index',
                    'Used for caching, counting, grouping'
                ]
            }
        ]
    },
]


def seed_notes():
    init_db()
    col = get_collection('notes')

    # Fast check
    if col.count_documents({}, limit=1) > 0:
        print('✓ Notes already seeded, skipping')
        return

    from datetime import datetime
    for note in NOTES:
        note['createdAt'] = datetime.utcnow()
        note['updatedAt'] = datetime.utcnow()

    col.insert_many(NOTES)
    print(f'✓ Seeded {len(NOTES)} notes')


if __name__ == '__main__':
    seed_notes()
    print('Done!')
