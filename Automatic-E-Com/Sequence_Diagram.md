# E-Commerce System Sequence Diagrams

## Main System Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Crawler
    participant Processor
    participant Database

    User->>Frontend: Search request
    Frontend->>API: GET /search?query=affiliate
    API->>Crawler: Trigger web crawl
    Crawler->>Database: Store raw data
    API->>Processor: Process content
    Processor->>Database: Store products
    API->>Frontend: Return results
    Frontend->>User: Display products
```

## Affiliate Integration Flow

```mermaid
sequenceDiagram
    participant System
    participant AffiliateAPI
    participant PaymentGateway

    System->>AffiliateAPI: GET programs
    AffiliateAPI-->>System: Return programs
    System->>AffiliateAPI: Select program
    AffiliateAPI-->>System: Confirm selection
    User->>System: Purchase product
    System->>PaymentGateway: Process payment
    PaymentGateway-->>System: Confirm payment
    System->>AffiliateAPI: Record transaction
```

## Content Processing Flow

```mermaid
sequenceDiagram
    participant Crawler
    participant NLP
    participant Generator
    participant Database

    Crawler->>Database: Store raw content
    Database->>NLP: Fetch for processing
    NLP->>NLP: Analyze/classify
    NLP->>Generator: Structured data
    Generator->>Generator: Create product
    Generator->>Database: Store final product
```

## Marketing Automation Flow

```mermaid
sequenceDiagram
    participant System
    participant SocialMedia
    participant EmailService

    System->>SocialMedia: Auto-post product
    SocialMedia-->>System: Post confirmation
    User->>SocialMedia: Engage with post
    SocialMedia->>System: Notify engagement
    System->>EmailService: Send follow-up
    EmailService-->>System: Delivery status
```

## Key Components
1. **User Interactions**: Search, purchase, engagement
2. **System Processes**: Crawling, processing, generation
3. **External Services**: Affiliate APIs, payment gateways
4. **Marketing Channels**: Social media, email