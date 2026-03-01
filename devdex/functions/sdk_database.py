from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SDKInfo:

    name: str
    data_collected: tuple[str, ...] = ()
    category: str = ""
    privacy_description: str = ""


SDK_PATTERNS: dict[str, SDKInfo] = {
    "import FirebaseAnalytics": SDKInfo(
        name="Firebase Analytics",
        data_collected=("device_id", "usage_data", "crash_data"),
        category="analytics",
        privacy_description="Collects device identifiers and app usage data for analytics purposes.",
    ),
    "import Firebase": SDKInfo(
        name="Firebase",
        data_collected=("device_id", "usage_data"),
        category="analytics",
        privacy_description="Firebase SDK may collect device and usage data.",
    ),
    "import Mixpanel": SDKInfo(
        name="Mixpanel",
        data_collected=("device_id", "usage_data", "user_profile"),
        category="analytics",
        privacy_description="Collects event data, device info, and user profiles for analytics.",
    ),
    "import Amplitude": SDKInfo(
        name="Amplitude",
        data_collected=("device_id", "usage_data"),
        category="analytics",
        privacy_description="Collects event and device data for product analytics.",
    ),
    "import AppsFlyerLib": SDKInfo(
        name="AppsFlyer",
        data_collected=("device_id", "advertising_id", "install_data"),
        category="attribution",
        privacy_description="Collects device identifiers and install attribution data.",
    ),
    "import FirebaseCrashlytics": SDKInfo(
        name="Firebase Crashlytics",
        data_collected=("crash_data", "device_id"),
        category="crash_reporting",
        privacy_description="Collects crash logs and device identifiers for crash reporting.",
    ),
    "import Sentry": SDKInfo(
        name="Sentry",
        data_collected=("crash_data", "device_id"),
        category="crash_reporting",
        privacy_description="Collects error and crash data for debugging purposes.",
    ),
    "import Alamofire": SDKInfo(
        name="Alamofire",
        data_collected=(),
        category="networking",
        privacy_description="HTTP networking library. Does not collect data on its own.",
    ),
    "import Moya": SDKInfo(
        name="Moya",
        data_collected=(),
        category="networking",
        privacy_description="Network abstraction layer. Does not collect data on its own.",
    ),
    "import SnapKit": SDKInfo(
        name="SnapKit",
        data_collected=(),
        category="ui",
        privacy_description="Auto Layout DSL. Does not collect data.",
    ),
    "import Kingfisher": SDKInfo(
        name="Kingfisher",
        data_collected=(),
        category="ui",
        privacy_description="Image loading library. Does not collect user data.",
    ),
    "import SDWebImage": SDKInfo(
        name="SDWebImage",
        data_collected=(),
        category="ui",
        privacy_description="Image loading library. Does not collect user data.",
    ),
    "import Lottie": SDKInfo(
        name="Lottie",
        data_collected=(),
        category="ui",
        privacy_description="Animation library. Does not collect user data.",
    ),
    "import GoogleSignIn": SDKInfo(
        name="Google Sign-In",
        data_collected=("email", "name", "user_id"),
        category="auth",
        privacy_description="Collects user email and profile for Google authentication.",
    ),
    "import AuthenticationServices": SDKInfo(
        name="Sign in with Apple",
        data_collected=("email", "name", "user_id"),
        category="auth",
        privacy_description="Apple authentication. User controls what data is shared.",
    ),
    "import FirebaseAuth": SDKInfo(
        name="Firebase Auth",
        data_collected=("email", "user_id"),
        category="auth",
        privacy_description="Manages user authentication with email, phone, or social providers.",
    ),
    "import GoogleMobileAds": SDKInfo(
        name="Google AdMob",
        data_collected=("device_id", "advertising_id", "usage_data", "location"),
        category="ads",
        privacy_description="Displays ads and collects device/advertising identifiers and location.",
    ),
    "import FBAudienceNetwork": SDKInfo(
        name="Facebook Audience Network",
        data_collected=("device_id", "advertising_id", "usage_data"),
        category="ads",
        privacy_description="Displays ads and collects device identifiers for ad targeting.",
    ),
    "import StoreKit": SDKInfo(
        name="StoreKit (In-App Purchases)",
        data_collected=("purchase_history",),
        category="payments",
        privacy_description="Handles in-app purchases via the App Store.",
    ),
    "import Stripe": SDKInfo(
        name="Stripe",
        data_collected=("payment_info",),
        category="payments",
        privacy_description="Processes payments. Collects payment card information.",
    ),
    "import RealmSwift": SDKInfo(
        name="Realm",
        data_collected=(),
        category="database",
        privacy_description="Local database. Does not collect user data unless Realm Sync is enabled.",
    ),
    "import CoreData": SDKInfo(
        name="Core Data",
        data_collected=(),
        category="database",
        privacy_description="Apple's local persistence framework. Does not transmit user data.",
    ),
    "from google.analytics": SDKInfo(
        name="Google Analytics",
        data_collected=("device_id", "usage_data", "location"),
        category="analytics",
        privacy_description="Collects browsing and usage data for web analytics.",
    ),
    "'react-ga'": SDKInfo(
        name="Google Analytics (React)",
        data_collected=("device_id", "usage_data"),
        category="analytics",
        privacy_description="React wrapper for Google Analytics.",
    ),
    "from sentry_sdk": SDKInfo(
        name="Sentry (Python)",
        data_collected=("crash_data", "device_id"),
        category="crash_reporting",
        privacy_description="Collects error data for debugging.",
    ),
    "import posthog": SDKInfo(
        name="PostHog",
        data_collected=("device_id", "usage_data", "user_profile"),
        category="analytics",
        privacy_description="Product analytics. Collects events and user data.",
    ),
    "'@stripe/stripe-js'": SDKInfo(
        name="Stripe.js",
        data_collected=("payment_info",),
        category="payments",
        privacy_description="Processes web payments.",
    ),
    "import RevenueCat": SDKInfo(
        name="RevenueCat",
        data_collected=("purchase_history", "device_id"),
        category="payments",
        privacy_description="Manages subscriptions and in-app purchases.",
    ),
    "import Purchases": SDKInfo(
        name="RevenueCat",
        data_collected=("purchase_history", "device_id"),
        category="payments",
        privacy_description="Manages subscriptions and in-app purchases.",
    ),
}


ENTITLEMENT_PATTERNS: dict[str, str] = {
    "com.apple.developer.healthkit": "HealthKit",
    "com.apple.developer.homekit": "HomeKit",
    "com.apple.security.application-groups": "App Groups",
    "com.apple.developer.associated-domains": "Associated Domains",
    "com.apple.developer.in-app-payments": "Apple Pay",
    "com.apple.developer.nfc.readersession.formats": "NFC",
    "com.apple.developer.siri": "Siri",
    "com.apple.developer.usernotifications.communication": "Communication Notifications",
    "aps-environment": "Push Notifications",
    "com.apple.developer.icloud-container-identifiers": "iCloud",
    "keychain-access-groups": "Keychain Sharing",
}


def match_import(line: str) -> SDKInfo | None:
    stripped = line.strip()
    best: SDKInfo | None = None
    best_len = 0
    for pattern, info in SDK_PATTERNS.items():
        if pattern in stripped and len(pattern) > best_len:
            best = info
            best_len = len(pattern)
    return best
