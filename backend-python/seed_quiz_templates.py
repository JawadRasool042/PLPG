"""
============================================
Seed Quiz Templates
============================================

Script to populate the database with initial quiz templates
for various interest categories and skill levels.
"""

from database import get_collection


def seed_quiz_templates():
    """Seed quiz templates into the database"""
    
    templates_coll = get_collection('quiz_templates')
    
    # Clear existing templates (optional - comment out to preserve existing)
    # templates_coll.delete_many({})
    
    templates = []
    
    # ========================================
    # AI/ML - Beginner
    # ========================================
    templates.extend([
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What does AI stand for?',
            'options': ['A) Automated Intelligence', 'B) Artificial Intelligence', 'C) Advanced Integration', 'D) Algorithmic Interface'],
            'answer': 'B',
            'explanation': 'AI stands for Artificial Intelligence, which refers to the simulation of human intelligence in machines.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'Which of the following is a supervised learning algorithm?',
            'options': ['A) K-Means Clustering', 'B) Linear Regression', 'C) Principal Component Analysis', 'D) Autoencoders'],
            'answer': 'B',
            'explanation': 'Linear Regression is a supervised learning algorithm that learns from labeled data to predict continuous values.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What is the primary goal of machine learning?',
            'options': ['A) To replace human workers', 'B) To enable computers to learn from data', 'C) To create robots', 'D) To build websites'],
            'answer': 'B',
            'explanation': 'Machine learning enables computers to learn patterns from data and make predictions or decisions without being explicitly programmed.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'Which Python library is most commonly used for machine learning?',
            'options': ['A) Django', 'B) Flask', 'C) Scikit-learn', 'D) Pandas'],
            'answer': 'C',
            'explanation': 'Scikit-learn is the most popular Python library for machine learning, providing simple and efficient tools for data analysis.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What is a neural network inspired by?',
            'options': ['A) Computer circuits', 'B) Human brain structure', 'C) Network routers', 'D) Database schemas'],
            'answer': 'B',
            'explanation': 'Neural networks are inspired by the structure and function of biological neural networks in the human brain.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What does the term "training data" refer to?',
            'options': ['A) Data used to test the model', 'B) Data used to teach the model', 'C) Data for production use', 'D) Backup data'],
            'answer': 'B',
            'explanation': 'Training data is the dataset used to teach (train) a machine learning model to recognize patterns and make predictions.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What is overfitting in machine learning?',
            'options': ['A) When a model is too simple', 'B) When a model performs well on training data but poorly on new data', 'C) When training takes too long', 'D) When the dataset is too large'],
            'answer': 'B',
            'explanation': 'Overfitting occurs when a model learns the training data too well, including noise, and fails to generalize to new data.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'Which of these is an example of classification?',
            'options': ['A) Predicting house prices', 'B) Identifying spam emails', 'C) Forecasting stock prices', 'D) Estimating temperature'],
            'answer': 'B',
            'explanation': 'Classification involves categorizing data into discrete classes, like identifying whether an email is spam or not spam.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What is a feature in machine learning?',
            'options': ['A) A bug in the code', 'B) An input variable used for prediction', 'C) The output of the model', 'D) A type of algorithm'],
            'answer': 'B',
            'explanation': 'A feature is an individual measurable property or characteristic of the data used as input for machine learning models.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What is the purpose of a validation set?',
            'options': ['A) To train the model', 'B) To tune hyperparameters and evaluate model performance', 'C) To deploy the model', 'D) To store predictions'],
            'answer': 'B',
            'explanation': 'A validation set is used to tune model hyperparameters and provide an unbiased evaluation during training.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'What does NLP stand for in AI?',
            'options': ['A) Natural Language Programming', 'B) Network Layer Protocol', 'C) Natural Language Processing', 'D) Neural Learning Process'],
            'answer': 'C',
            'explanation': 'NLP stands for Natural Language Processing, which deals with the interaction between computers and human language.'
        },
        {
            'interest': 'AI/ML',
            'level': 'Beginner',
            'question': 'Which metric is commonly used for classification models?',
            'options': ['A) Mean Squared Error', 'B) Accuracy', 'C) R-squared', 'D) Standard Deviation'],
            'answer': 'B',
            'explanation': 'Accuracy measures the proportion of correct predictions and is a common metric for evaluating classification models.'
        },
    ])
    
    # ========================================
    # Web Development - Beginner
    # ========================================
    templates.extend([
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What does HTML stand for?',
            'options': ['A) Hyper Text Markup Language', 'B) High Tech Modern Language', 'C) Home Tool Markup Language', 'D) Hyperlinks and Text Markup Language'],
            'answer': 'A',
            'explanation': 'HTML stands for Hyper Text Markup Language, the standard language for creating web pages.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which HTML tag is used to define an internal style sheet?',
            'options': ['A) <script>', 'B) <style>', 'C) <css>', 'D) <link>'],
            'answer': 'B',
            'explanation': 'The <style> tag is used to define internal CSS styles within an HTML document.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What does CSS stand for?',
            'options': ['A) Creative Style Sheets', 'B) Computer Style Sheets', 'C) Cascading Style Sheets', 'D) Colorful Style Sheets'],
            'answer': 'C',
            'explanation': 'CSS stands for Cascading Style Sheets, used to style and layout web pages.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which property is used to change the background color in CSS?',
            'options': ['A) color', 'B) bgcolor', 'C) background-color', 'D) bg-color'],
            'answer': 'C',
            'explanation': 'The background-color property is used to set the background color of an element in CSS.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What is JavaScript primarily used for?',
            'options': ['A) Styling web pages', 'B) Making web pages interactive', 'C) Structuring web content', 'D) Database management'],
            'answer': 'B',
            'explanation': 'JavaScript is primarily used to add interactivity and dynamic behavior to web pages.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which tag is used to create a hyperlink in HTML?',
            'options': ['A) <link>', 'B) <a>', 'C) <href>', 'D) <url>'],
            'answer': 'B',
            'explanation': 'The <a> (anchor) tag is used to create hyperlinks in HTML.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What is the correct HTML element for the largest heading?',
            'options': ['A) <heading>', 'B) <h6>', 'C) <h1>', 'D) <head>'],
            'answer': 'C',
            'explanation': 'The <h1> tag defines the largest and most important heading in HTML.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which symbol is used to select an ID in CSS?',
            'options': ['A) .', 'B) #', 'C) *', 'D) @'],
            'answer': 'B',
            'explanation': 'The # symbol is used to select elements by their ID in CSS.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What does the "DOM" stand for?',
            'options': ['A) Document Object Model', 'B) Data Object Management', 'C) Digital Optimization Method', 'D) Display Object Module'],
            'answer': 'A',
            'explanation': 'DOM stands for Document Object Model, representing the structure of an HTML document as a tree of objects.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which HTTP method is used to retrieve data?',
            'options': ['A) POST', 'B) PUT', 'C) GET', 'D) DELETE'],
            'answer': 'C',
            'explanation': 'GET is the HTTP method used to request and retrieve data from a server.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'What is Bootstrap?',
            'options': ['A) A JavaScript library', 'B) A CSS framework', 'C) A programming language', 'D) A database'],
            'answer': 'B',
            'explanation': 'Bootstrap is a popular CSS framework for developing responsive and mobile-first websites.'
        },
        {
            'interest': 'Web Development',
            'level': 'Beginner',
            'question': 'Which tag is used to define a table row in HTML?',
            'options': ['A) <table>', 'B) <td>', 'C) <tr>', 'D) <th>'],
            'answer': 'C',
            'explanation': 'The <tr> tag is used to define a table row in HTML.'
        },
    ])
    
    # ========================================
    # Cybersecurity - Beginner
    # ========================================
    templates.extend([
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What does "phishing" refer to in cybersecurity?',
            'options': ['A) Catching computer viruses', 'B) Fraudulent attempts to obtain sensitive information', 'C) Network scanning', 'D) Password encryption'],
            'answer': 'B',
            'explanation': 'Phishing is a cyberattack method where attackers fraudulently attempt to obtain sensitive information like passwords and credit card details.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is malware?',
            'options': ['A) Software that protects computers', 'B) Malicious software designed to harm systems', 'C) A type of firewall', 'D) An antivirus program'],
            'answer': 'B',
            'explanation': 'Malware is any software intentionally designed to cause damage to a computer, server, or network.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What does VPN stand for?',
            'options': ['A) Virtual Private Network', 'B) Very Protected Network', 'C) Verified Public Network', 'D) Virtual Public Node'],
            'answer': 'A',
            'explanation': 'VPN stands for Virtual Private Network, which creates a secure connection over the internet.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is the primary purpose of a firewall?',
            'options': ['A) To speed up internet', 'B) To block unauthorized access', 'C) To encrypt files', 'D) To backup data'],
            'answer': 'B',
            'explanation': 'A firewall monitors and controls incoming and outgoing network traffic to block unauthorized access.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is two-factor authentication?',
            'options': ['A) Using two passwords', 'B) Security method requiring two forms of identification', 'C) Two firewalls', 'D) Dual antivirus software'],
            'answer': 'B',
            'explanation': 'Two-factor authentication (2FA) is a security process requiring two different forms of identification to verify identity.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is a "strong password" characteristic?',
            'options': ['A) Easy to remember', 'B) Contains only letters', 'C) Long with mixed characters, numbers, and symbols', 'D) Your name and birth date'],
            'answer': 'C',
            'explanation': 'A strong password is long and includes a mix of uppercase and lowercase letters, numbers, and special symbols.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What does "encryption" mean?',
            'options': ['A) Deleting data', 'B) Converting data into a coded format', 'C) Backing up files', 'D) Scanning for viruses'],
            'answer': 'B',
            'explanation': 'Encryption converts data into a coded format that can only be read with the correct decryption key.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is ransomware?',
            'options': ['A) Free software', 'B) Malware that locks files and demands payment', 'C) A type of antivirus', 'D) A security protocol'],
            'answer': 'B',
            'explanation': 'Ransomware is malware that encrypts a victim\'s files and demands payment to restore access.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What does HTTPS indicate?',
            'options': ['A) High Performance Transfer', 'B) Secure HTTP connection', 'C) Hypertext Protocol System', 'D) Home Page Transfer Service'],
            'answer': 'B',
            'explanation': 'HTTPS (Hypertext Transfer Protocol Secure) indicates a secure, encrypted connection to a website.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is social engineering in cybersecurity?',
            'options': ['A) Building social networks', 'B) Manipulating people to divulge confidential information', 'C) Engineering social media sites', 'D) Creating user profiles'],
            'answer': 'B',
            'explanation': 'Social engineering is the psychological manipulation of people into performing actions or divulging confidential information.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What should you do if you receive a suspicious email?',
            'options': ['A) Click all links to check them', 'B) Forward it to everyone', 'C) Delete it or report it as spam', 'D) Reply with your password'],
            'answer': 'C',
            'explanation': 'Suspicious emails should be deleted or reported as spam/phishing without clicking any links or attachments.'
        },
        {
            'interest': 'Cybersecurity',
            'level': 'Beginner',
            'question': 'What is antivirus software?',
            'options': ['A) Software that creates viruses', 'B) Software that detects and removes malware', 'C) A type of operating system', 'D) A web browser'],
            'answer': 'B',
            'explanation': 'Antivirus software detects, prevents, and removes malware from computer systems.'
        },
    ])
    
    # ========================================
    # Data Science - Beginner
    # ========================================
    templates.extend([
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is data science?',
            'options': ['A) The study of data structures', 'B) Extracting insights and knowledge from data', 'C) Creating databases', 'D) Building websites'],
            'answer': 'B',
            'explanation': 'Data science involves extracting meaningful insights and knowledge from structured and unstructured data.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'Which Python library is used for data manipulation?',
            'options': ['A) NumPy', 'B) Pandas', 'C) Matplotlib', 'D) Scikit-learn'],
            'answer': 'B',
            'explanation': 'Pandas is the primary Python library for data manipulation and analysis, providing data structures like DataFrames.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is a DataFrame?',
            'options': ['A) A type of chart', 'B) A 2-dimensional labeled data structure', 'C) A database', 'D) A programming framework'],
            'answer': 'B',
            'explanation': 'A DataFrame is a 2-dimensional labeled data structure with columns of potentially different types, similar to a spreadsheet.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What does EDA stand for?',
            'options': ['A) Electronic Data Analysis', 'B) Exploratory Data Analysis', 'C) Extended Database Architecture', 'D) Efficient Data Algorithms'],
            'answer': 'B',
            'explanation': 'EDA (Exploratory Data Analysis) is the process of analyzing datasets to summarize their main characteristics.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'Which visualization library is popular in Python?',
            'options': ['A) Django', 'B) Flask', 'C) Matplotlib', 'D) TensorFlow'],
            'answer': 'C',
            'explanation': 'Matplotlib is the most widely used Python library for creating static, interactive, and animated visualizations.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is the mean of a dataset?',
            'options': ['A) The most frequent value', 'B) The middle value', 'C) The average value', 'D) The range of values'],
            'answer': 'C',
            'explanation': 'The mean is the average value of a dataset, calculated by summing all values and dividing by the count.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is the median?',
            'options': ['A) The average value', 'B) The middle value when sorted', 'C) The most common value', 'D) The difference between max and min'],
            'answer': 'B',
            'explanation': 'The median is the middle value in a dataset when arranged in ascending or descending order.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is correlation?',
            'options': ['A) Data storage method', 'B) Relationship between two variables', 'C) Type of chart', 'D) Database query'],
            'answer': 'B',
            'explanation': 'Correlation measures the statistical relationship between two variables, indicating how they change together.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is missing data?',
            'options': ['A) Deleted files', 'B) Values that are not recorded in the dataset', 'C) Backup data', 'D) Encrypted information'],
            'answer': 'B',
            'explanation': 'Missing data refers to values that are not recorded or available in the dataset for certain observations.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is data cleaning?',
            'options': ['A) Deleting all data', 'B) Removing errors and inconsistencies from data', 'C) Encrypting data', 'D) Backing up data'],
            'answer': 'B',
            'explanation': 'Data cleaning is the process of detecting and correcting errors, inconsistencies, and inaccuracies in datasets.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What is a histogram used for?',
            'options': ['A) Showing trends over time', 'B) Displaying the distribution of data', 'C) Comparing categories', 'D) Showing relationships between variables'],
            'answer': 'B',
            'explanation': 'A histogram is used to display the distribution of numerical data by grouping values into bins.'
        },
        {
            'interest': 'Data Science',
            'level': 'Beginner',
            'question': 'What does SQL stand for?',
            'options': ['A) Structured Query Language', 'B) Simple Question Language', 'C) System Quality Level', 'D) Standard Query Logic'],
            'answer': 'A',
            'explanation': 'SQL (Structured Query Language) is the standard language for managing and querying relational databases.'
        },
    ])
    
    # Add more categories as needed (Cloud Computing, Mobile Development, etc.)
    # For brevity, keeping initial set focused on 4 main categories
    
    # Insert templates
    if templates:
        # Fast check: if collection already has data, skip entirely
        existing_count = templates_coll.count_documents({}, limit=1)
        if existing_count > 0:
            print(f'✓ Quiz templates already seeded, skipping')
            return

        templates_coll.insert_many(templates)
        print(f'* Seeded {len(templates)} quiz templates')
        print(f'  - AI/ML: 12 questions (Beginner)')
        print(f'  - Web Development: 12 questions (Beginner)')
        print(f'  - Cybersecurity: 12 questions (Beginner)')
        print(f'  - Data Science: 12 questions (Beginner)')
    else:
        print('No templates to seed')


if __name__ == '__main__':
    from database import init_db
    
    print('Initializing database...')
    init_db()
    
    print('\nSeeding quiz templates...')
    seed_quiz_templates()
    
    print('\n* Seeding complete!')
