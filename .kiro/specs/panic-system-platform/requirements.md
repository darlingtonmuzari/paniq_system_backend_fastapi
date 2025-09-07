# Requirements Document

## Introduction

The Panic System Platform is a comprehensive emergency response platform that connects security firms, emergency service providers, and end users. The system enables security firms to create subscription products that users can purchase to access emergency services including security, ambulance, fire, and towing services. The platform manages user groups, mobile number verification, credit systems, and real-time emergency response coordination through mobile applications.

## Requirements

### Requirement 1

**User Story:** As a security firm, I want to register on the platform and get verified, so that I can offer emergency response services to users.

#### Acceptance Criteria

1. WHEN a security firm submits registration details THEN the system SHALL store their information for verification
2. WHEN the platform admin reviews a security firm application THEN the system SHALL allow approval or rejection with reasons
3. IF a security firm is approved THEN the system SHALL activate their account and notify them
4. WHEN a security firm is approved THEN the system SHALL allow them to define service coverage areas with GPS boundaries
5. WHEN a security firm is approved THEN the system SHALL allow them to create subscription products

### Requirement 2

**User Story:** As a security firm, I want to purchase panic credits, so that I can create subscription products for my customers.

#### Acceptance Criteria

1. WHEN a security firm initiates credit purchase THEN the system SHALL provide payment options (credit/debit card, bank transfer)
2. WHEN payment is processed successfully THEN the system SHALL add credits to the firm's account
3. WHEN creating a subscription product THEN the system SHALL deduct credits based on product configuration
4. IF insufficient credits exist THEN the system SHALL prevent product creation and display credit balance

### Requirement 3

**User Story:** As a security firm, I want to create subscription products with pricing and user limits, so that registered users can purchase emergency services.

#### Acceptance Criteria

1. WHEN creating a subscription product THEN the system SHALL require maximum user count, price, and 1-month expiration window
2. WHEN a subscription product is created THEN the system SHALL deduct appropriate panic credits from firm's balance
3. WHEN a subscription is purchased THEN the system SHALL track usage against maximum user limits
4. IF user limit is reached THEN the system SHALL prevent additional users from joining the subscription
5. WHEN a product is purchased THEN the system SHALL add 1 month to the group subscription expiration date

### Requirement 4

**User Story:** As a registered user, I want to purchase subscriptions and manage groups of mobile numbers, so that my group members can access emergency services.

#### Acceptance Criteria

1. WHEN a user purchases a subscription THEN the system SHALL store it in the user's profile without automatically applying it
2. WHEN a user applies a stored subscription to a group THEN the system SHALL verify the group address is within the security firm's coverage area
3. IF group address is within coverage THEN the system SHALL create or extend the group with expiry date based on product's 1-month window
4. IF group address is outside coverage THEN the system SHALL reject the application and suggest alternative security firms
5. WHEN adding mobile numbers to a group THEN the system SHALL verify each number and assign user types (individual, alarm, camera)
6. WHEN a group is created THEN the system SHALL require one address and GPS coordinates
7. WHEN applying a subscription for renewal THEN the system SHALL extend the existing group expiry date by 1 month
8. WHEN a subscription is applied THEN the system SHALL remove it from the user's stored subscriptions

### Requirement 5

**User Story:** As a registered user, I want to apply my purchased subscriptions to groups, so that I can manage emergency services for my mobile numbers.

#### Acceptance Criteria

1. WHEN a user has stored subscriptions in their profile THEN the system SHALL allow them to apply each subscription to only one group
2. WHEN applying a subscription THEN the system SHALL prevent transfer or sharing with other users
3. WHEN a subscription is applied to a group THEN the system SHALL create or extend that specific group with mobile numbers that can send panic requests
4. WHEN a subscription is applied THEN the system SHALL mark it as used and prevent application to other groups
5. IF a user attempts to apply an already-used subscription THEN the system SHALL reject the action and display an error message
6. IF a user attempts to transfer a subscription THEN the system SHALL reject the action and display an error message

### Requirement 6

**User Story:** As a mobile app user, I want to send panic requests for different emergency services, so that I can get help when needed.

#### Acceptance Criteria

1. WHEN a user sends a panic request THEN the system SHALL offer service types: call, security, ambulance, fire services, towing
2. WHEN a panic request is submitted THEN the system SHALL verify the user has a valid subscription
3. WHEN a panic request is submitted THEN the system SHALL verify the request location is within the security firm's coverage area
4. IF user has valid subscription AND location is covered THEN the system SHALL process the emergency request
5. IF location is outside coverage area THEN the system SHALL reject the request and notify the user
6. WHEN a call service is requested THEN the system SHALL set the requester's phone to silent mode (no ring, no vibration)

### Requirement 7

**User Story:** As a security firm, I want to enroll field agents and office staff, so that they can respond to emergency requests.

#### Acceptance Criteria

1. WHEN enrolling users THEN the system SHALL distinguish between field agents, team leaders, and office staff roles
2. WHEN a field agent is enrolled THEN the system SHALL provide them mobile app access for receiving requests
3. WHEN a team leader is enrolled THEN the system SHALL provide them mobile app access and team management capabilities
4. WHEN office staff are enrolled THEN the system SHALL provide them control room access for request allocation
5. WHEN organizing field personnel THEN the system SHALL allow assignment of field agents to teams under team leaders
6. WHEN a panic request comes in THEN the system SHALL allow office staff to allocate requests to teams or individual agents

### Requirement 8

**User Story:** As a field agent, I want to receive and accept allocated panic requests, so that I can respond to emergencies.

#### Acceptance Criteria

1. WHEN office staff allocates a request THEN the system SHALL send notification to assigned field agent's mobile app
2. WHEN a field agent receives a request THEN the system SHALL require acceptance before proceeding
3. WHEN a field agent accepts a request THEN the system SHALL update request status and notify all parties
4. IF request type is "call" THEN the system SHALL NOT assign to field agents and require office staff to handle directly

### Requirement 9

**User Story:** As a security firm, I want to register external service providers (ambulance, towing, fire), so that I can coordinate comprehensive emergency response.

#### Acceptance Criteria

1. WHEN adding service providers THEN the system SHALL require address, email, phone number, and GPS coordinates
2. WHEN a panic request matches service type THEN the system SHALL calculate distances to available providers
3. WHEN service provider is selected THEN the system SHALL send request details to their mobile app
4. WHEN service provider accepts THEN the system SHALL share vehicle details with the requester

### Requirement 10

**User Story:** As a service provider, I want to receive emergency requests and track user locations, so that I can provide timely assistance.

#### Acceptance Criteria

1. WHEN an emergency request is assigned THEN the system SHALL send location and contact details to service provider's mobile app
2. WHEN service provider accepts request THEN the system SHALL enable location tracking between provider and requester
3. WHEN service provider is en route THEN the system SHALL send real-time updates to requester about estimated arrival time
4. WHEN service provider arrives THEN the system SHALL notify requester with vehicle identification details

### Requirement 11

**User Story:** As a requester, I want to receive real-time updates about my emergency request, so that I know when help is arriving.

#### Acceptance Criteria

1. WHEN an emergency request is submitted THEN the system SHALL provide immediate confirmation with request ID
2. WHEN service provider is assigned THEN the system SHALL send provider details and estimated arrival time
3. WHEN service provider location changes THEN the system SHALL update estimated arrival time in real-time
4. WHEN service provider arrives THEN the system SHALL send notification with vehicle identification details

### Requirement 12

**User Story:** As a platform administrator, I want to verify and approve companies and service providers, so that only legitimate entities can use the platform.

#### Acceptance Criteria

1. WHEN a company registers THEN the system SHALL require verification documents and business details
2. WHEN reviewing applications THEN the system SHALL provide admin interface for approval/rejection decisions
3. WHEN approving entities THEN the system SHALL activate their accounts and send confirmation notifications
4. IF rejecting applications THEN the system SHALL provide rejection reasons and allow resubmission

### Requirement 13

**User Story:** As a field team member, I want to provide feedback after completing a service request, so that the system can track performance and identify prank requests.

#### Acceptance Criteria

1. WHEN a service request is completed THEN the system SHALL require the responding team to provide feedback
2. WHEN providing feedback THEN the system SHALL allow teams to flag requests as prank calls
3. WHEN a request is flagged as prank THEN the system SHALL record it against the requester's profile
4. WHEN feedback is submitted THEN the system SHALL store performance metrics for monitoring and tracking
5. IF multiple prank flags are recorded for a user THEN the system SHALL automatically flag the user for review

### Requirement 14

**User Story:** As a platform administrator, I want to fine users who make prank requests, so that I can discourage misuse of emergency services.

#### Acceptance Criteria

1. WHEN a user accumulates prank flags THEN the system SHALL calculate fines based on prank frequency
2. WHEN fines are applied THEN the system SHALL notify the user and provide payment options
3. WHEN fines remain unpaid THEN the system SHALL suspend the user's access to emergency services
4. WHEN fines are paid THEN the system SHALL restore user access and reset prank counters
5. IF prank behavior continues after fines THEN the system SHALL permanently ban the user from the platform

### Requirement 15

**User Story:** As a security firm manager, I want to track response time metrics by zone and service type, so that I can monitor and improve service performance.

#### Acceptance Criteria

1. WHEN a panic request is submitted THEN the system SHALL record the timestamp and location zone
2. WHEN a field team accepts a request THEN the system SHALL record the acceptance timestamp
3. WHEN a field team arrives at location THEN the system SHALL record the arrival timestamp
4. WHEN service is completed THEN the system SHALL calculate total response time from request to arrival
5. WHEN calculating metrics THEN the system SHALL group response times by geographical zone and service type
6. WHEN generating reports THEN the system SHALL provide average, minimum, and maximum response times per zone per service
7. WHEN performance degrades THEN the system SHALL alert security firm managers about zones with poor response times

### Requirement 16

**User Story:** As a platform administrator, I want to ensure mobile app integrity and prevent unauthorized access, so that only genuine apps can access emergency services.

#### Acceptance Criteria

1. WHEN field staff, registered users, or mobile users make API requests THEN the system SHALL require app integrity attestation through mobile endpoints
2. WHEN using Android apps THEN the system SHALL verify Google Play Integrity API attestation tokens
3. WHEN using iOS apps THEN the system SHALL verify Apple App Attest attestation tokens
4. WHEN attestation verification fails THEN the system SHALL reject API requests and log security incidents
5. WHEN attestation is valid THEN the system SHALL process requests normally
6. WHEN detecting modified or tampered apps THEN the system SHALL block access and notify administrators
7. WHEN implementing attestation THEN the system SHALL use cryptographically-signed tokens to verify app authenticity
8. WHEN field staff access the system THEN they SHALL use mobile endpoints with attestation (not web interfaces)
9. WHEN registered users manage subscriptions and groups THEN they SHALL use mobile endpoints with attestation
10. WHEN mobile users send panic requests THEN they SHALL use mobile endpoints with attestation