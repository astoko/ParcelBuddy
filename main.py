import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
gi.require_version('GdkPixbuf', '2.0')

import sys
import threading
import json
import os
import pprint
import shutil
import subprocess
from datetime import datetime
from dotenv import load_dotenv, dotenv_values 
from gi.repository import Gtk, Adw, GLib, Gio, Pango, Gdk, GdkPixbuf
import requests

env_file = os.path.join(GLib.get_user_data_dir(),'.env')
print(f"Loading environment from: {env_file}")
base_env_file = "/app/config/.env"

if not os.path.exists(env_file):
    shutil.copy(base_env_file, env_file)

load_dotenv(env_file)

# ---------------- Tracker class ----------------
class Tracker:
    """Handles all API interactions for tracking."""
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    GRAPHQL_URL = os.getenv("GRAPHQL_URL")

    CARRIERS = {
        "Cainiao Global": "cn.cainiao.global",
        "DHL": "de.dhl",
        "Sagawa": "jp.sagawa",
        "Yamato": "jp.yamato",
        "ACT&CORE (Ocean Inbound)": "kr.actcore.ocean-inbound",
        "CJ Logistics": "kr.cjlogistics",
        "Coupang Logistics Services": "kr.coupangls",
        "CUpost": "kr.cupost",
        "Chunilps": "kr.chunilps",
        "GS Postbox": "kr.cvsnet",
        "CWAY (Woori Express)": "kr.cway",
        "Daesin": "kr.daesin",
        "LX Pantos": "kr.epantos",
        "Korea Post": "kr.epost",
        "Korea Post EMS": "kr.epost.ems",
        "GoodsToLuck": "kr.goodstoluck",
        "HomePick": "kr.homepick",
        "Hanjin": "kr.hanjin",
        "Honam Logis": "kr.honamlogis",
        "Ilyang Logis": "kr.ilyanglogis",
        "Kyoungdong": "kr.kdexp",
        "Kunyoung": "kr.kunyoung",
        "Logen": "kr.logen",
        "Lotte": "kr.lotte",
        "Lotte Global": "kr.lotte.global",
        "LTL": "kr.ltl",
        "SLX": "kr.slx",
        "Sungwon Global Cargo (Korea Post)": "kr.swgexp.epost",
        "Sungwon Global Cargo (CJ Logistics)": "kr.swgexp.cjlogistics",
        "Today Pickup": "kr.todaypickup",
        "Yongma Logis": "kr.yongmalogis",
        "TNT": "nl.tnt",
        "EMS": "un.upu.ems",
        "Fedex": "us.fedex",
        "UPS": "us.ups",
        "USPS": "us.usps",
        "HPL": "kr.hanips",
        "Hapdong": "kr.hdexp",
        "Yuubin": "jp.yuubin",
    }
    
    # Updated to use courier-specific icon paths
    # Icons are stored in the icons/couriers directory
    CARRIER_ICONS = {
        "Cainiao Global": "couriers/cainiao",
        "DHL": "couriers/dhl",
        "CJ Logistics": "couriers/cjlogistics",
        "Fedex": "couriers/fedex",
        "TNT": "couriers/tnt",
        "UPS": "couriers/ups",
        "USPS": "couriers/usps",
        "Coupang Logistics Services": "couriers/missing",
        "CUpost": "couriers/missing",
        "Chunilps": "couriers/missing",
        "GS Postbox": "couriers/missing",
        "CWAY (Woori Express)": "couriers/missing",
        "Daesin": "couriers/missing",
        "LX Pantos": "couriers/missing",
        "Korea Post": "couriers/missing",
        "Korea Post EMS": "couriers/missing",
        "GoodsToLuck": "couriers/missing",
        "HomePick": "couriers/missing",
        "Hanjin": "couriers/missing",
        "Honam Logis": "couriers/missing",
        "Ilyang Logis": "couriers/missing",
        "Kyoungdong": "couriers/missing",
        "Kunyoung": "couriers/missing",
        "Logen": "couriers/missing",
        "Lotte": "couriers/missing",
        "Lotte Global": "couriers/missing",
        "LTL": "couriers/missing",
        "SLX": "couriers/missing",
        "Sungwon Global Cargo (Korea Post)": "couriers/missing",
        "Sungwon Global Cargo (CJ Logistics)": "couriers/missing",
        "Today Pickup": "couriers/missing",
        "Yongma Logis": "couriers/missing",
        "EMS": "couriers/missing",
        "HPL": "couriers/missing",
        "Hapdong": "couriers/missing",
        "Yuubin": "couriers/missing"
    }


    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.log("⚙️ Initializing Tracker class.")
        self.auth_header = f"TRACKQL-API-KEY {self.CLIENT_ID}:{self.CLIENT_SECRET}"
        self.log("✅ Tracker class initialized.")

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)


    def get_carriers(self):
        carriers = {}
        after = None

        while True:
            track_response = requests.post(
                url=self.GRAPHQL_URL,
                headers={
                    "Authorization": f"TRACKQL-API-KEY {self.CLIENT_ID}:{self.CLIENT_SECRET}"
                },
                json={
                    "query": """
                        query CarrierList($after: String) {
                            carriers(first: 40, after: $after) {
                                pageInfo {
                                    hasNextPage
                                    endCursor
                                }
                                edges {
                                    node {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                        """,
                    "variables": {"after": after},
                }
            ).json()

            # Debug print
            print("API Response:")
            pprint.pprint(track_response)

            if 'data' not in track_response or track_response['data'] is None:
                print("❌ API error or empty response")
                break

            for edge in track_response['data']['carriers']['edges']:
                node = edge['node']
                # Prefer displayName if available, otherwise fall back to name
                label = node.get('displayName') or node.get('name') or node['id']
                carriers[label] = node['id']

            page_info = track_response['data']['carriers']['pageInfo']
            if page_info['hasNextPage']:
                after = page_info['endCursor']
            else:
                break

        return carriers



    def get_tracking_status(self, tracking_number: str, carrier_name: str):
        self.log(f"📡 Sending API request for {tracking_number} with carrier {carrier_name}...")
        
        carriers = self.get_carriers()
        
        # Look up the carrier ID by name
        carrier_id = carriers.get(carrier_name)
        if not carrier_id:
            self.log(f"❌ Carrier '{carrier_name}' not supported. Aborting.")
            raise Exception(f"Carrier '{carrier_name}' not supported")

        query = """
        query Track($carrierId: ID!, $trackingNumber: String!) {
        track(carrierId: $carrierId, trackingNumber: $trackingNumber) {
            lastEvent {
            time
            status {
                code
                name
            }
            description
            }
            events(last: 10) {
            edges {
                node {
                time
                status {
                    code
                    name
                }
                description
                }
            }
            }
        }
        }
        """
        variables = {"carrierId": carrier_id, "trackingNumber": tracking_number}
        self.log("📄 GraphQL query and variables prepared.")

        try:
            response = requests.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json",
                        "Authorization": f"TRACKQL-API-KEY {self.CLIENT_ID}:{self.CLIENT_SECRET}"},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            track_info = data.get("data", {}).get("track")
            if not track_info:
                self.log("❗ No tracking information found in the API response.")
                raise Exception("No tracking information found for this number.")
            
            self.log("👍 API response received and parsed successfully.")

            result = {"last_event": None, "events": []}
            last = track_info.get("lastEvent")
            if last:
                result["last_event"] = {
                    "time": self._format_time(last["time"]),
                    "status_code": last["status"]["code"],
                    "status_name": last["status"]["name"],
                    "description": last.get("description", "")
                }
                self.log(f"⭐ Last event found: {result['last_event']['status_name']}")
            
            for edge in track_info.get("events", {}).get("edges", []):
                node = edge.get("node")
                if node:
                    result["events"].append({
                        "time": self._format_time(node["time"]),
                        "status_code": node["status"]["code"],
                        "status_name": node["status"]["name"],
                        "description": node.get("description", "")
                    })
            self.log(f"📜 Processed {len(result['events'])} events from the timeline.")
            
            if result["events"]:
                result["events"].sort(key=lambda x: datetime.fromisoformat(x['time'].replace("Z", "+00:00")))
                
            return result

        except requests.Timeout:
            self.log("❗ Request timed out.")
            raise Exception("Request timed out")
        except requests.RequestException as e:
            self.log(f"❌ Network error occurred: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            self.log(f"❌ An unexpected error occurred: {str(e)}")
            raise Exception(f"Error: {str(e)}")


    def _format_time(self, iso_time: str):
        self.log(f"⏰ Formatting time: {iso_time}")
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            self.log(f"✅ Time formatted to: {formatted_time}")
            return formatted_time
        except Exception as e:
            self.log(f"⚠️ Error formatting time: {e}. Returning original string.")
            return iso_time

    def send_notification(self, title: str, message: str):
        """Sends a desktop notification if the system supports it."""
        self.log(f"🔔 Sending desktop notification: '{title}' - '{message}'")
        try:
            subprocess.run(["notify-send", "--app-name=Parcel Buddy", title, message])
            self.log("✅ Notification sent successfully.")
        except Exception as e:
            GLib.idle_add(self.log, f"⚠️ Failed to send notification: {e}")


# ---------------- Icon Mapping ----------------
class IconHelper:
    """Helper class for icon names with fallbacks"""
    # Icon mapping using GTK's standard symbolic icons
    STATUS_ICONS = {
        "information_received": "dialog-information-symbolic",
        "at_pickup": "location-services-active-symbolic",
        "in_transit": "emoji-travel-symbolic",
        "out_for_delivery": "send-to-symbolic",
        "attempt_fail": "dialog-warning-symbolic",
        "delivered": "emoji-flags-symbolic",
        "available_for_pickup": "folder-download-symbolic",
        "exception": "action-unavailable-symbolic",
        "error": "action-unavailable-symbolic",
        "unknown": "dialog-question-symbolic",
        "package": "package-x-generic-symbolic",
        "place": "mark-location-symbolic",
        "transit": "emoji-travel-symbolic"
    }
    
    # Icon mapping for UI elements
    UI_ICONS = {
        "arrow_back": "go-previous-symbolic",
        "refresh": "view-refresh-symbolic",
        "add": "list-add-symbolic",
        "menu": "open-menu-symbolic",
        "open_in_new": "window-new-symbolic",
        "package": "package-x-generic-symbolic"
    }

    @staticmethod
    def get_icon_name(name):
        # Try status icons first
        if name in IconHelper.STATUS_ICONS:
            return IconHelper.STATUS_ICONS[name]
        # Try UI icons
        if name in IconHelper.UI_ICONS:
            return IconHelper.UI_ICONS[name]
        # Fallback to package icon
        return "package-x-generic-symbolic"
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        # Try custom icon first
        custom_name = IconHelper.CUSTOM_ICONS.get(name)
        if custom_name:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", f"{custom_name}.svg")
            if os.path.exists(icon_path):
                return custom_name
            
        # Try symbolic fallback
        fallback = IconHelper.SYMBOLIC_FALLBACKS.get(name)
        if fallback:
            return fallback
            
        # Get icon theme
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        # Try custom icon first
        custom_name = IconHelper.CUSTOM_ICONS.get(name)
        if custom_name and icon_theme.has_icon(custom_name):
            return custom_name
            
        # Ultimate fallback
        return "package-x-generic-symbolic"
            
        # Try symbolic fallback
        fallback = IconHelper.SYMBOLIC_FALLBACKS.get(name)
        if fallback and icon_theme.has_icon(fallback):
            return fallback
            
        # Ultimate fallback
        return "package-x-generic-symbolic"
        
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        # First try the material icon name
        if icon_theme.has_icon(name):
            return name
            
        # Then try the fallback symbolic icon
        fallback = MATERIAL_TO_SYMBOLIC.get(name)
        if fallback and icon_theme.has_icon(fallback):
            return fallback
            
        # Ultimate fallback
        return "package-x-generic-symbolic"

# ---------------- Status Codes ----------------
class TrackEventStatusCode:
    """Defines and provides helper methods for tracking status codes."""
    UNKNOWN = "UNKNOWN"
    INFORMATION_RECEIVED = "INFORMATION_RECEIVED"
    AT_PICKUP = "AT_PICKUP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    ATTEMPT_FAIL = "ATTEMPT_FAIL"
    DELIVERED = "DELIVERED"
    AVAILABLE_FOR_PICKUP = "AVAILABLE_FOR_PICKUP"
    EXCEPTION = "EXCEPTION"

    @staticmethod
    def get_icon(status_code: str):
        icon_name = {
            TrackEventStatusCode.INFORMATION_RECEIVED: "information_received",
            TrackEventStatusCode.AT_PICKUP: "at_pickup",
            TrackEventStatusCode.IN_TRANSIT: "in_transit",
            TrackEventStatusCode.OUT_FOR_DELIVERY: "out_for_delivery",
            TrackEventStatusCode.ATTEMPT_FAIL: "attempt_fail",
            TrackEventStatusCode.DELIVERED: "delivered",
            TrackEventStatusCode.AVAILABLE_FOR_PICKUP: "available_for_pickup",
            TrackEventStatusCode.EXCEPTION: "exception",
            TrackEventStatusCode.UNKNOWN: "unknown",
        }.get(status_code, "package")
        return IconHelper.get_icon_name(icon_name)

    @staticmethod
    def get_pretty_name(status_code: str):
        return {
            TrackEventStatusCode.INFORMATION_RECEIVED: "Info Received",
            TrackEventStatusCode.AT_PICKUP: "Ready for Pickup",
            TrackEventStatusCode.IN_TRANSIT: "In Transit",
            TrackEventStatusCode.OUT_FOR_DELIVERY: "Out for Delivery",
            TrackEventStatusCode.ATTEMPT_FAIL: "Delivery Attempt Failed",
            TrackEventStatusCode.DELIVERED: "Delivered",
            TrackEventStatusCode.AVAILABLE_FOR_PICKUP: "Available for Pickup",
            TrackEventStatusCode.EXCEPTION: "Exception",
            TrackEventStatusCode.UNKNOWN: "Unknown Status",
        }.get(status_code, status_code.replace('_', ' ').title())

    @staticmethod
    def get_color_class(status_code: str):
        return {
            TrackEventStatusCode.DELIVERED: "delivered",
            TrackEventStatusCode.OUT_FOR_DELIVERY: "outfordelivery",
            TrackEventStatusCode.IN_TRANSIT: "intransit",
            TrackEventStatusCode.AVAILABLE_FOR_PICKUP: "pickup",
            TrackEventStatusCode.ATTEMPT_FAIL: "exception",
            TrackEventStatusCode.EXCEPTION: "exception",
        }.get(status_code, "unknown")


# ---------------- Main Window ----------------
class ParcelWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loading_log_buffer = None
        self.log_text_view = None
        self.tracker = Tracker(self.log_message)
        self.data_file = os.path.join(GLib.get_user_data_dir(), 'parcelbuddy', 'history.json')
        #if os.path.exists("/.flatpak-info"):
        # Running inside Flatpak
        if os.path.exists("/.flatpak-info"):
            self.icons_dir = "/app/share/parcelapp/icons"
        else:
            # Running outside Flatpak
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            self.icons_dir = os.path.join(self.app_dir, "icons")

        self.update_source_id = None
        self.parcel_cards = {}
        self.refresh_countdown_seconds = 60
        self.pending_updates = 0
        self.setup_window()
        self.create_actions()
        self.build_ui()
        self.log_message("✅ ParcelWindow and UI are ready.")
        self.load_history()

    def log_message(self, message):
        # All log updates must be handled by the main thread.
        GLib.idle_add(self._update_log_ui, message)

    def _update_log_ui(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry, end='')
        
        if self.loading_log_buffer:
            end_iter = self.loading_log_buffer.get_end_iter()
            self.loading_log_buffer.insert(end_iter, log_entry)
            self._scroll_log_to_end()
        return GLib.SOURCE_REMOVE

    def _scroll_log_to_end(self):
        if self.log_text_view:
            adj = self.log_text_view.get_vadjustment()
            adj.set_value(adj.get_upper())

    # ---------------- Setup ----------------
    def setup_window(self):
        self.log_message("🛠️ Setting up window properties.")
        self.set_default_size(700, 650)
        self.set_title("Parcel Buddy")
        style_manager = Adw.StyleManager.get_default()
        self.log_message("✅ Window setup complete.")

    # ---------------- Actions ----------------
    def create_actions(self):
        self.log_message("✨ Creating window actions.")
        actions = [("clear_history", self.on_clear_history), ("about", self.on_about)]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', callback)
            self.add_action(action)
        self.log_message("✅ Actions created and added.")
    
    def on_clear_history(self, action, param):
        self.log_message("🗑️ Clear history action triggered.")
        self.save_history([])
        self.load_history()
        self.log_message("✅ History cleared.")

    def on_about(self, action, param):
        self.log_message("ℹ️ About action triggered.")
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Parcel Buddy",
            application_icon="share/hicolor/128x128/io.github.astoko.ParcelBuddy.png",
            developer_name="Astoko",
            version="0.1.4",
            comments="A simple app to track your parcels."
        )
        about.present()
        self.log_message("✅ 'About' window presented.")

    def on_manual_refresh(self, _widget):
        self.log_message("🔄 Manual refresh triggered. Showing spinner...")
        self.show_toast("Checking for parcel updates...")
        self.stack.set_visible_child_name("loading")
        if self.loading_log_buffer:
            self.loading_log_buffer.set_text("")
        self.check_for_updates()
        
    def show_toast(self, message):
        """Helper to display a toast message."""
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)
        
    def open_tracking_link(self, widget, courier_id, tracking_number):
        self.log_message(f"🔗 Opening tracking link for {tracking_number}...")
        url = f"https://link.tracker.delivery/track?client_id={self.tracker.CLIENT_ID}&carrier_id={courier_id}&tracking_number={tracking_number}"
        try:
            subprocess.Popen(['xdg-open', url])
        except FileNotFoundError:
            self.log_message("❌ xdg-open not found. Please open the link manually.")

    # ---------------- UI ----------------

    def build_ui(self):
        self.log_message("🏗️ Building the main UI.")
        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        # --- Header Buttons ---
        self.back_button = Gtk.Button(icon_name=IconHelper.get_icon_name("arrow_back"))
        self.back_button.set_tooltip_text("Go Back")
        self.back_button.connect("clicked", self.on_back_clicked)
        header.pack_start(self.back_button)

        self.add_button = Gtk.Button(icon_name=IconHelper.get_icon_name("add"))
        self.add_button.add_css_class("suggested-action")
        self.add_button.set_tooltip_text("Add New Parcel")
        self.add_button.connect("clicked", self.on_add_clicked)
        header.pack_start(self.add_button)

        self.refresh_button = Gtk.Button(icon_name=IconHelper.get_icon_name("refresh"))
        self.refresh_button.set_tooltip_text("Manual Refresh")
        self.refresh_button.add_css_class("flat")
        self.refresh_button.connect("clicked", self.on_manual_refresh)
        header.pack_start(self.refresh_button)

        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_child(Gtk.SearchEntry())
        self.search_bar.get_child().set_placeholder_text("Search parcels...")
        self.search_bar.get_child().connect("search-changed", self.on_search_changed)
        header.pack_start(self.search_bar)

        menu = Gio.Menu.new()
        menu.append("Clear History", "win.clear_history")
        menu.append("About", "win.about")
        menu_button = Gtk.MenuButton(icon_name=IconHelper.get_icon_name("menu"), menu_model=menu)
        header.pack_end(menu_button)

        # --- Main container ---
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        self.toast_overlay = Adw.ToastOverlay()
        main_box.append(self.toast_overlay)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        self.stack.connect("notify::visible-child", self.on_stack_page_changed)
        self.toast_overlay.set_child(self.stack)

        # --- Add pages ---
        self.stack.add_named(self.create_page_dashboard(), "dashboard")
        self.stack.add_named(self.create_page_loading(), "loading")
        self.stack.add_named(self.create_page_results(), "results")
        self.stack.add_named(self.create_page_error(), "error")
        # New onboarding page creation
        self.stack.add_named(self._create_page_onboarding(), "onboarding")

        # --- Show onboarding if credentials missing ---
        CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
        CLIENT_SECRET = os.getenv("CLIENT_SECRET", "").strip()
        GRAPHQL_URL = os.getenv("GRAPHQL_URL", "").strip()

        if not CLIENT_ID or not CLIENT_SECRET or not GRAPHQL_URL:
            self.stack.set_visible_child_name("onboarding")
            self.log_message("↔️ No API credentials found, showing onboarding page.")
        else:
            self.stack.set_visible_child_name("dashboard")
            self.log_message("↔️ Credentials found, showing dashboard page.")


    # --- NEW & IMPROVED ONBOARDING UI ---
    def _create_page_onboarding(self):
        self.log_message("📝 Creating new onboarding page.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        status_page = Adw.StatusPage(
            icon_name="io.github.astoko.ParcelBuddy",
            title="Welcome to Parcel Buddy!",
            description="""To get started, please enter your API credentials from <a href="https://tracker.delivery/en/">tracker.delivery</a>."""
        )
        status_page.set_vexpand(True)
        status_page.set_valign(Gtk.Align.CENTER)
        box.append(status_page)
        
        # Clamp to limit the width of the input fields
        clamp = Adw.Clamp(maximum_size=400)
        
        credentials_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        credentials_box.set_margin_top(12)
        credentials_box.set_margin_bottom(12)
        
        self.input_client_id = Gtk.Entry(placeholder_text="CLIENT_ID")
        credentials_box.append(self.input_client_id)

        self.input_client_secret = Gtk.Entry(placeholder_text="CLIENT_SECRET")
        credentials_box.append(self.input_client_secret)

        graphql_url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.input_graphql_url = Gtk.Entry(placeholder_text="GRAPHQL_URL")
        self.input_graphql_url.set_hexpand(True)
        graphql_url_box.append(self.input_graphql_url)

        self.default_url_check = Gtk.CheckButton(label="Use default")
        self.default_url_check.set_active(True)
        self.default_url_check.connect("toggled", self._on_default_url_toggled)
        graphql_url_box.append(self.default_url_check)

        self.input_graphql_url.set_text("https://apis.tracker.delivery/graphql")
        self.input_graphql_url.set_editable(False)
        credentials_box.append(graphql_url_box)
        
        # Test and Save buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        self.feedback_spinner = Gtk.Spinner()
        self.feedback_label = Gtk.Label(label="", xalign=0.5, wrap=True)
        
        self.test_button = Gtk.Button(label="Test Credentials")
        self.test_button.add_css_class("suggested-action")
        self.test_button.connect("clicked", self._on_test_credentials_clicked)
        button_box.append(self.test_button)

        self.save_button = Gtk.Button(label="Save & Continue")
        self.save_button.add_css_class("suggested-action")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self._on_save_credentials_clicked)
        button_box.append(self.save_button)
        
        credentials_box.append(button_box)
        credentials_box.append(self.feedback_spinner)
        credentials_box.append(self.feedback_label)

        clamp.set_child(credentials_box)
        box.append(clamp)
        return box

    def _on_default_url_toggled(self, check_button):
        GRAPHQL_URL = os.getenv("GRAPHQL_URL")
        is_active = check_button.get_active()
        self.input_graphql_url.set_editable(not is_active)
        if is_active:
            self.input_graphql_url.set_text(f"{GRAPHQL_URL}")
            
    def _on_test_credentials_clicked(self, _widget):
        client_id = self.input_client_id.get_text().strip()
        client_secret = self.input_client_secret.get_text().strip()
        graphql_url = self.input_graphql_url.get_text().strip()
        
        if not client_id or not client_secret or not graphql_url:
            self.feedback_label.set_text("Please fill all fields.")
            return

        self.feedback_spinner.set_spinning(True)
        self.feedback_label.set_text("Testing...")
        self.save_button.set_sensitive(False)

        def test_in_background():
            try:
                # Temporarily update the tracker instance's credentials
                original_client_id = self.tracker.CLIENT_ID
                original_client_secret = self.tracker.CLIENT_SECRET
                original_graphql_url = self.tracker.GRAPHQL_URL

                self.tracker.CLIENT_ID = client_id
                self.tracker.CLIENT_SECRET = client_secret
                self.tracker.GRAPHQL_URL = graphql_url

                # Attempt to get carriers to validate credentials
                self.tracker.get_carriers()
                
                # Restore original credentials (if test succeeds)
                GLib.idle_add(lambda: self._on_test_success())
            except Exception as e:
                # Restore original credentials (if test fails)
                self.tracker.CLIENT_ID = original_client_id
                self.tracker.CLIENT_SECRET = original_client_secret
                self.tracker.GRAPHQL_URL = original_graphql_url
                GLib.idle_add(lambda e=e: self._on_test_failure(e))

        threading.Thread(target=test_in_background, daemon=True).start()

    def _on_test_success(self):
        self.feedback_spinner.set_spinning(False)
        self.feedback_label.set_markup("<span foreground='green'>✅ Credentials are valid!</span>")
        self.save_button.set_sensitive(True)

    def _on_test_failure(self, error):
        self.feedback_spinner.set_spinning(False)
        self.feedback_label.set_markup(f"<span foreground='red'>❌ Test failed: {str(error)}</span>")
        self.save_button.set_sensitive(False)

    def _on_save_credentials_clicked(self, _widget):
        client_id = self.input_client_id.get_text().strip()
        client_secret = self.input_client_secret.get_text().strip()
        graphql_url = self.input_graphql_url.get_text().strip()

        # Save to .env
        env_path = os.path.join(GLib.get_user_data_dir(),'.env')
        
        with open(env_path, "w") as f:
            f.write(f"CLIENT_ID={client_id}\n")
            f.write(f"CLIENT_SECRET={client_secret}\n")
            f.write(f"GRAPHQL_URL={graphql_url}\n")
        
        # Also update os.environ for immediate use
        os.environ["CLIENT_ID"] = client_id
        os.environ["CLIENT_SECRET"] = client_secret
        os.environ["GRAPHQL_URL"] = graphql_url
        
        # Update the tracker instance's credentials
        self.tracker.CLIENT_ID = client_id
        self.tracker.CLIENT_SECRET = client_secret
        self.tracker.GRAPHQL_URL = graphql_url
        
        self.show_toast("Credentials saved successfully.")
        self.stack.set_visible_child_name("dashboard")
        self.load_history()
        self.check_for_updates()
        self.update_source_id = GLib.timeout_add(1000, self.update_countdown_label)


    def on_test_tracking_clicked(self, _widget):
        tracking_number = "1234567890"
        carrier_name = "kr.cjlogistics"

        # Check credentials
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        GRAPHQL_URL = os.getenv("GRAPHQL_URL")

        client_id = self.input_client_id.get_text().strip()
        client_secret = self.input_client_secret.get_text().strip()
        graphql_url = self.input_graphql_url.get_text().strip()

        if not client_id or not client_secret or not graphql_url:
            self.log_message("❌ Please fill all API fields before testing.")
            return

        self.log_message(f"📡 Testing tracking for {tracking_number} with {carrier_name}...")
        try:
            tracker = Tracker(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, graphql_url=GRAPHQL_URL)
            result = tracker.get_tracking_status(tracking_number, carrier_name)
            self.log_message(f"✅ Test tracking successful: Last status = {result['last_event']['status_name']}")
        except Exception as e:
            self.log_message(f"❌ Test tracking failed: {str(e)}")


    def on_back_clicked(self, _widget):
        self.log_message("⬅️ Going back to the dashboard.")
        self.stack.set_visible_child_name("dashboard")

    def on_onboarding_submit(self, button):
        client_id = self.client_id_entry.get_text().strip()
        client_secret = self.client_secret_entry.get_text().strip()
        
        if not client_id or not client_secret:
            self.onboarding_status_label.set_text("❌ Both fields are required.")
            return
        env_path = os.path.join(GLib.get_user_data_dir(),'.env')
        # Save to .env (simple overwrite)
        with open(env_path, "w") as f:
            f.write(f"CLIENT_ID={CLIENT_ID}\n")
            f.write(f"CLIENT_SECRET={CLIENT_SECRET}\n")
            f.write(f"GRAPHQL_URL={GRAPHQL_URL}\n")  # change if needed
        
        # Test with example parcel number
        from datetime import datetime
        try:
            result = self.tracker.get_tracking_status("1234567890", "kr.cjlogistics")
            self.onboarding_status_label.set_text("✅ Credentials valid! Showing dashboard...")
            # Switch to dashboard
            self.stack.set_visible_child_name("dashboard")
        except Exception as e:
            self.onboarding_status_label.set_text(f"❌ Test failed: {str(e)}")

    def on_stack_page_changed(self, stack, _param):
        page_name = stack.get_visible_child_name()
        # Show back button on all pages except dashboard
        if page_name == "onboarding":
            self.add_button.set_visible(False)
            self.back_button.set_visible(False)
            self.search_bar.set_visible(False)
            self.refresh_button.set_visible(False)
        if page_name == "dashboard":
            self.add_button.set_visible(True)
            self.search_bar.set_visible(False)
            self.refresh_button.set_visible(True)
            self.back_button.set_visible(False)
        if page_name == "results":
            self.back_button.set_visible(True)
            self.add_button.set_visible(False)
            self.search_bar.set_visible(False)
            self.refresh_button.set_visible(False)
        if page_name == "loading":
            self.back_button.set_visible(True)
            self.add_button.set_visible(False)
            self.refresh_button.set_visible(False)

        self.log_message(f"↔️ Stack page changed to: {stack.get_visible_child_name()}")
        
    def on_search_changed(self, search_entry):
        query = search_entry.get_text().lower().strip()
        self.log_message(f"🔍 Search query: '{query}'")
        for child in self.parcel_flowbox.get_children():
            name = child.name.lower()
            visible = not query or query in name
            child.set_visible(visible)

    # ---------------- Pages ----------------
    def create_page_dashboard(self):
        self.log_message("🖼️ Creating dashboard page.")
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10)
        
        self.scrolled = Gtk.ScrolledWindow(vexpand=True)
        self.clamp = Adw.Clamp(maximum_size=1200)
        
        # New FlowBox for the grid layout
        self.parcel_flowbox = Gtk.FlowBox()
        self.parcel_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.parcel_flowbox.set_valign(Gtk.Align.START)
        self.parcel_flowbox.set_homogeneous(True)
        self.parcel_flowbox.set_row_spacing(10)
        self.parcel_flowbox.set_column_spacing(10)
        self.parcel_flowbox.set_min_children_per_line(1)
        
        self.clamp.set_child(self.parcel_flowbox)
        self.scrolled.set_child(self.clamp)
        main_box.append(self.scrolled)
        return main_box

    def create_page_loading(self):
        self.log_message("🔄 Creating loading page.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, vexpand=True, valign=Gtk.Align.CENTER, margin_top=20)
        
        spinner = Gtk.Spinner(spinning=True, height_request=48, width_request=48)
        label = Gtk.Label(label="Fetching tracking data...", margin_bottom=10)
        label.add_css_class("dim-label")
        box.append(spinner)
        box.append(label)

        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, hexpand=True)
        log_frame = Gtk.Frame(label="Activity Log")
        log_frame.add_css_class("card")
        
        log_scrolled_window = Gtk.ScrolledWindow()
        log_scrolled_window.set_vexpand(True)
        log_scrolled_window.set_size_request(-1, 200)
        
        self.loading_log_buffer = Gtk.TextBuffer()
        self.log_text_view = Gtk.TextView(buffer=self.loading_log_buffer, margin_start=10, margin_end=10, margin_top=10, margin_bottom=10)
        self.log_text_view.set_editable(False)
        self.log_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_text_view.add_css_class("log-text")
        
        log_scrolled_window.set_child(self.log_text_view)
        log_frame.set_child(log_scrolled_window)
        
        clamp = Adw.Clamp(maximum_size=800)
        clamp.set_child(log_frame)
        box.append(clamp)
        
        return box

    def create_page_results(self):
        self.log_message("📊 Creating results page.")
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrolled.set_child(main_box)
        
        # Add padding to the main container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        clamp = Adw.Clamp(maximum_size=800)
        clamp.set_child(content_box)
        main_box.append(clamp)
        
        # --- Top Section with Status and Progress Bar ---
        top_frame = Gtk.Frame()
        top_frame.add_css_class("card")
        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        top_box.set_margin_top(16)
        top_box.set_margin_bottom(16)
        top_box.set_margin_start(16)
        top_box.set_margin_end(16)
        top_frame.set_child(top_box)
        
        # Header with title and buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_bottom(8)
        
        self.status_label = Gtk.Label(xalign=0, hexpand=True)
        self.status_label.set_markup('<span size="x-large" weight="bold">Parcel Status</span>')
        header_box.append(self.status_label)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        tracking_button = Gtk.Button()
        tracking_button.set_icon_name(IconHelper.get_icon_name("web-browser-symbolic"))
        tracking_button.set_tooltip_text("Open Tracking Link")
        tracking_button.add_css_class("flat")
        tracking_button.connect("clicked", self.on_tracking_link_clicked)
        button_box.append(tracking_button)

        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.set_tooltip_text("Copy Tracking Number")
        copy_button.add_css_class("flat")
        copy_button.connect("clicked", self.on_copy_tracking_clicked)
        button_box.append(copy_button)

        
        remove_button = Gtk.Button()
        remove_button.set_icon_name("edit-delete-symbolic")
        remove_button.set_tooltip_text("Remove from History")
        remove_button.add_css_class("flat")
        remove_button.connect("clicked", self.on_remove_tracking_clicked)
        button_box.append(remove_button)
        
        header_box.append(button_box)
        top_box.append(header_box)
        
        # Status details
        self.details_label = Gtk.Label(xalign=0, wrap=True)
        self.details_label.set_margin_bottom(8)
        self.details_label.add_css_class("caption")
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_margin_top(8)
        
        top_box.append(self.details_label)
        top_box.append(self.progress_bar)
        content_box.append(top_frame)

        # --- Timeline Section ---
        timeline_header = Gtk.Label(xalign=0)
        timeline_header.set_markup('<span size="large" weight="bold">Tracking Timeline</span>')
        timeline_header.set_margin_top(16)
        timeline_header.set_margin_bottom(8)
        content_box.append(timeline_header)
        
        timeline_frame = Gtk.Frame()
        timeline_frame.add_css_class("card")
        self.timeline_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.timeline_box.set_margin_top(16)
        self.timeline_box.set_margin_bottom(16)
        self.timeline_box.set_margin_start(16)
        self.timeline_box.set_margin_end(16)
        self.timeline_box.add_css_class("timeline-container")
        timeline_frame.set_child(self.timeline_box)
        content_box.append(timeline_frame)
        
        return scrolled

    def create_page_error(self):
        self.log_message("❗ Creating error page.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True, valign=Gtk.Align.CENTER)
        icon = Gtk.Image.new_from_icon_name(IconHelper.get_icon_name("exception"))
        icon.set_pixel_size(64)
        self.error_label = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        box.append(icon); box.append(self.error_label)
        return box

    # ---------------- Tracking Logic ----------------
    def on_add_clicked(self, _widget):
        self.log_message("➕ 'Add New Parcel' button clicked. Presenting dialog.")
        dialog = Adw.MessageDialog(transient_for=self, modal=True,
            heading="Add New Parcel", body="Enter name, courier, and tracking number.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "OK")
        dialog.set_response_enabled("ok", False)
        self.name_entry = Gtk.Entry(placeholder_text="Parcel Name")
        self.number_entry = Gtk.Entry(placeholder_text="Tracking Number")
        self.number_entry.connect("changed", lambda e: dialog.set_response_enabled("ok", bool(e.get_text().strip())))
        couriers = list(self.tracker.CARRIERS.keys())
        self.courier_model = Gtk.StringList.new(couriers)
        self.courier_dropdown = Gtk.DropDown(model=self.courier_model)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(self.name_entry)
        box.append(self.number_entry)
        box.append(self.courier_dropdown)
        dialog.set_extra_child(box)
        dialog.connect("response", self.on_add_dialog_response)
        dialog.present()
        self.log_message("✅ Add parcel dialog presented.")

    def on_add_dialog_response(self, dialog, response):
        self.log_message(f"📝 Add dialog response received: '{response}'.")
        if response == "ok":
            name = self.name_entry.get_text().strip()
            number = self.number_entry.get_text().strip()
            courier_item = self.courier_dropdown.get_selected_item()
            courier = courier_item.get_string() if courier_item else ""
            self.log_message(f"✅ User confirmed adding: Name='{name}', Number='{number}', Courier='{courier}'.")
            if number and courier:
                self.start_tracking(name, number, courier, is_new_parcel=True, show_results_page=True)
        else:
            self.log_message("🚫 Add parcel dialog cancelled.")
        dialog.close()

    def start_tracking(self, name, number, courier, is_new_parcel=False, show_results_page=True):
        self.log_message(f"🔍 Starting tracking process for '{name}' with number '{number}' via {courier}...")
        if show_results_page:
            self.stack.set_visible_child_name("loading")
        threading.Thread(target=self.track_in_background, args=(name, number, courier, is_new_parcel, show_results_page), daemon=True).start()
        self.log_message("✅ Tracking thread started.")

    def track_in_background(self, name, number, courier, is_new_parcel, show_results_page):
        self.log_message(f"🏃‍♀️ Starting {'background' if not is_new_parcel else 'initial'} tracking thread for {name} ({number})...")
        try:
            info = self.tracker.get_tracking_status(number, courier)
            GLib.idle_add(self.on_tracking_success, name, number, courier, info, is_new_parcel, show_results_page)
            self.log_message("✅ Tracking data fetched. Sending to main thread.")
        except Exception as e:
            self.log_message(f"❌ Error in tracking thread for {number}: {e}")
            GLib.idle_add(self.on_tracking_error, e, is_new_parcel, show_results_page)

    def on_tracking_success(self, name, number, courier, info, is_new_parcel, show_results_page):
        self.log_message("🎉 Received successful tracking data on the main thread.")
        last_event = info.get("last_event")
        events = info.get("events", [])
        
            # Calculate days in transit
        days_in_transit = "N/A"
        if events:
            # Events are already sorted chronologically by the tracker
            first_event_time_str = events[0].get('time')
            if first_event_time_str:
                first_event_date = datetime.fromisoformat(first_event_time_str.replace("Z", "+00:00")).date()
                # Use delivery date for delivered packages, current date for others
                if last_event and last_event['status_code'] == TrackEventStatusCode.DELIVERED:
                    end_date = datetime.fromisoformat(last_event['time'].replace("Z", "+00:00")).date()
                else:
                    end_date = datetime.now().date()
                delta = end_date - first_event_date
                days_in_transit = f"{delta.days} day{'s' if delta.days != 1 else ''}"
        
        should_notify = False
        if is_new_parcel:
            should_notify = True
        else:
            history = self.get_history_data()
            old_status = next((item.get('last_status') for item in history if item.get('number') == number), None)
            if old_status and last_event and old_status != last_event['status_code']:
                self.log_message(f"✅ Status change detected for {name}: {old_status} -> {last_event['status_code']}")
                should_notify = True
        
        if should_notify and last_event:
            self.tracker.send_notification(f"Tracking Status Updated: {name}", last_event.get("description", ""))

        self.add_to_history(name, number, courier, last_event['status_code'] if last_event else 'UNKNOWN', last_event['time'] if last_event else None, days_in_transit, is_new_parcel)
        self.update_parcel_card_status(name, number, last_event, courier, days_in_transit)

        if self.pending_updates > 0 and not show_results_page:
            self.pending_updates -= 1
            if self.pending_updates == 0:
                self.log_message("🏁 All pending updates completed. Returning to dashboard.")
                self.stack.set_visible_child_name("dashboard")
        
        if show_results_page:
            if last_event:
                self.log_message("📋 Updating results page with new data.")
                
                # Update top section and store current parcel info
                self.current_parcel = {"name": name, "number": number, "courier": courier}
                self.status_label.set_markup(f'<span size="x-large" weight="bold">{name}</span><span size="small" foreground="#808080"> ({courier})</span>')
                pretty_name = TrackEventStatusCode.get_pretty_name(last_event['status_code'])
                self.details_label.set_markup(f'<b>#{number}</b>\n<b>{pretty_name}</b>\n<span size="small" foreground="#808080">{last_event["time"]}</span>\n<small>{last_event.get("description", "")}</small>')
                progress_fraction = 1.0 if last_event['status_code'] == TrackEventStatusCode.DELIVERED else 0.5
                self.progress_bar.set_fraction(progress_fraction)
                for css_class in ["delivered", "intransit", "outfordelivery", "pickup", "exception", "unknown"]:
                    self.progress_bar.remove_css_class(css_class)
                self.progress_bar.add_css_class(TrackEventStatusCode.get_color_class(last_event['status_code']))
                
                # Clear and populate timeline
                for child in list(self.timeline_box):
                    self.timeline_box.remove(child)
                self.log_message(f"📜 Populating timeline with {len(events)} events.")
                for event in reversed(events):
                    event_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15, halign=Gtk.Align.START)
                    
                    # Vertical box to hold the icon and spacer, to create the vertical line effect
                    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    vbox.set_size_request(20, -1)
                    vbox.add_css_class("timeline-event-vbox")
                    vbox.add_css_class(TrackEventStatusCode.get_color_class(event['status_code']))
                    
                    # Create the icon circle
                    icon_circle = Gtk.Box(halign=Gtk.Align.CENTER)
                    icon_circle.add_css_class("timeline-icon-circle")
                    icon = Gtk.Image.new_from_icon_name(TrackEventStatusCode.get_icon(event['status_code']))
                    icon.set_pixel_size(16)
                    icon_circle.append(icon)
                    vbox.append(icon_circle)
                    
                    # Create a flexible spacer to extend the vertical line
                    spacer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
                    vbox.append(spacer)
                    
                    # This is the actual content box for the event text
                    label = Gtk.Label(xalign=0)
                    desc = event.get("description", "")
                    pretty_name = TrackEventStatusCode.get_pretty_name(event['status_code'])
                    label.set_markup(f'<b>{pretty_name}</b>\n<span size="small" foreground="#808080">{event["time"]}</span>\n<small>{desc}</small>')
                    label.set_wrap(True)
                    label.set_hexpand(True)
                    
                    event_box.append(vbox)
                    event_box.append(label)
                    self.timeline_box.append(event_box)

                self.stack.set_visible_child_name("results")
            else:
                self.log_message("⚠️ No last event found. Cannot update results page.")

        self.log_message("✅ UI updated successfully.")

    def on_tracking_error(self, error, is_new_parcel=False, show_results_page=False):
        self.log_message(f"❌ A tracking error occurred: {error}")
        if show_results_page:
            msg = str(error)
            if "not found" in msg.lower(): msg = "Tracking number not found."
            elif "timeout" in msg.lower(): msg = "Request timed out."
            self.error_label.set_text(msg)
            self.stack.set_visible_child_name("error")
            self.log_message("🚨 Displaying error page.")
        
        if self.pending_updates > 0 and not show_results_page:
            self.pending_updates -= 1
            if self.pending_updates == 0:
                self.log_message("🏁 All pending updates completed. Returning to dashboard.")
                self.stack.set_visible_child_name("dashboard")

    def update_countdown_label(self):
        self.refresh_countdown_seconds -= 1
        minutes, seconds = divmod(self.refresh_countdown_seconds, 60)
        if self.refresh_countdown_seconds <= 0:
            self.check_for_updates()
        return GLib.SOURCE_CONTINUE

    def check_for_updates(self):
        self.log_message("🔄 Checking for parcel updates...")
        self.refresh_countdown_seconds = 1800
        history = self.get_history_data()
        self.pending_updates = len(history)
        if not history:
            self.log_message("📭 No parcels to check for updates.")
            self.stack.set_visible_child_name("dashboard")
            return GLib.SOURCE_CONTINUE
        self.log_message(f"🔎 Found {len(history)} parcels to check.")
        for item in history:
            name = item.get('name')
            number = item.get('number')
            courier = item.get('courier')
            self.log_message(f"🔎 Initiating update check for '{name}' ({number})...")
            threading.Thread(target=self.track_in_background, args=(name, number, courier, False, False), daemon=True).start()
        return GLib.SOURCE_CONTINUE

    # ---------------- History ----------------
    def load_history(self):
        self.log_message("📂 Loading parcel history...")
        history = []
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f: history = json.load(f)
                self.log_message(f"✅ Found history file with {len(history)} items.")
            except Exception as e: 
                self.log_message(f"⚠️ Error loading history file: {e}. Starting with empty history.")
                history = []
        
        self.parcel_cards = {}
        while child := self.parcel_flowbox.get_first_child():
            self.parcel_flowbox.remove(child)
        
        if not history: 
            self.log_message("✨ History is empty. Displaying empty state.")
            self.scrolled.set_child(self.create_empty_state_box())
            return
        else:
            self.scrolled.set_child(self.clamp)

        for item in history:
            card = self.create_parcel_card(item['name'], item['number'], item['courier'], item.get('last_status', 'UNKNOWN'), item.get('last_updated_time', ''), item.get('days_in_transit', "N/A"))
            self.parcel_flowbox.append(card)
            self.parcel_cards[item['number']] = card
            self.log_message(f"🖼️ Created card for '{item['name']}' ({item['number']}).")

    def save_history(self, history_data):
        self.log_message("💾 Saving parcel history...")
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try: 
            with open(self.data_file, 'w') as f:
                json.dump(history_data, f, indent=4)
            self.log_message("✅ History saved successfully.")
        except Exception as e: 
            self.log_message(f"❌ Error saving history: {e}")

    def add_to_history(self, name, number, courier, status, time, days_in_transit, is_new_parcel):
        self.log_message(f"Adding '{name}' to history...")
        history = self.get_history_data()
        
        history = [t for t in history if t.get('number') != number]
        
        new_entry = {'name': name, 'number': number, 'courier': courier, 'last_status': status, 'last_updated_time': time, 'days_in_transit': days_in_transit}
        history.insert(0, new_entry)
        
        self.save_history(history[:10])
        
        if is_new_parcel:
            card = self.create_parcel_card(name, number, courier, status, time, days_in_transit)
            self.parcel_cards[number] = card
            self.parcel_flowbox.insert(card, 0)
            self.scrolled.set_child(self.clamp)
            
        self.log_message("➕ Parcel added/updated in history.")

    def update_parcel_card_status(self, name, number, last_event, courier, days_in_transit):
        self.log_message(f"🔄 Updating card status for parcel {number}...")
        if number in self.parcel_cards:
            card_box = self.parcel_cards[number]
            
            card_box.title_label.set_text(name)
            card_box.courier_label.set_markup(f'<small>{courier}</small>')
            card_box.number_label.set_markup(f'<small>{number}</small>')
            
            pretty_name = TrackEventStatusCode.get_pretty_name(last_event['status_code'])
            self.log_message(f"  - Status changed to: {pretty_name}")
            card_box.status_label.set_markup(f'<b>{pretty_name}</b>')
            
            # Update days in transit label
            card_box.days_in_transit_label.set_markup(f'<small>{days_in_transit}</small>')
            
            # Update the progress bar and color classes
            progress_bar = card_box.progress_bar
            progress_fraction = 1.0 if last_event['status_code'] == TrackEventStatusCode.DELIVERED else 0.5
            progress_bar.set_fraction(progress_fraction)
            for css_class in ["delivered", "intransit", "outfordelivery", "pickup", "exception", "unknown"]:
                progress_bar.remove_css_class(css_class)
                card_box.remove_css_class(css_class)
            
            progress_bar.add_css_class(TrackEventStatusCode.get_color_class(last_event['status_code']))
            card_box.add_css_class(TrackEventStatusCode.get_color_class(last_event['status_code']))

            self.log_message(f"✅ Card for {number} updated.")
        else:
            self.log_message(f"⚠️ Card for {number} not found. Cannot update status.")

    def get_history_data(self):
        self.log_message("🔍 Fetching history data for operations...")
        if os.path.exists(self.data_file):
            try: 
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.log_message(f"✅ Fetched {len(data)} items from history file.")
                    return data
            except Exception as e:
                self.log_message(f"❌ Failed to read history data: {e}. Returning empty list.")
                return []
        self.log_message("⚠️ History file not found. Returning empty list.")
        return []
        
    def on_tracking_link_clicked(self, button):
        self.log_message("🔗 Opening tracking link...")
        history = self.get_history_data()
        for item in history:
            if item.get('name') in self.status_label.get_text():
                carrier_id = self.tracker.CARRIERS.get(item['courier'])
                tracking_number = item['number']
                if carrier_id:
                    url = f"https://link.tracker.delivery/track?client_id={self.tracker.CLIENT_ID}&carrier_id={carrier_id}&tracking_number={tracking_number}"
                    try:
                        subprocess.Popen(['xdg-open', url])
                        self.log_message("✅ Opened tracking link in browser")
                    except FileNotFoundError:
                        self.log_message("❌ xdg-open not found. Please open the link manually.")
                break
    
    def on_remove_tracking_clicked(self, button):
        self.log_message("🗑️ Removing tracking from history...")
        history = self.get_history_data()
        for item in history:
            if item.get('name') in self.status_label.get_text():
                history.remove(item)
                self.save_history(history)
                self.log_message("✅ Item removed from history")
                self.stack.set_visible_child_name("dashboard")
                self.load_history()
                self.show_toast("Tracking removed from history")
                break
                
    def on_copy_tracking_clicked(self, button):
        self.log_message("📋 Copying tracking number...")
        history = self.get_history_data()
        for item in history:
            if item.get('name') in self.status_label.get_text():
                clipboard = Gdk.Display.get_default().get_clipboard()
                provider = Gdk.ContentProvider.new_for_value(item['number'])
                clipboard.set_content(provider)
                self.log_message(f"✅ Copied tracking number: {item['number']}")
                self.show_toast("Tracking number copied to clipboard")
                break

    # ---------------- UI Helpers ----------------
    def create_empty_state_box(self):
        self.log_message("📦 Creating empty state UI.")
        status_page = Adw.StatusPage()
        
        status_page.set_icon_name("package-x-generic-symbolic")
        status_page.set_title("No Parcels Found")
        status_page.set_description("Add a new parcel to get started.")
        return status_page

    def create_parcel_card(self, name, number, courier, last_status, last_updated_time, days_in_transit):
        self.log_message(f"🖼️ Creating UI card for '{name}'...")
        
        # Main card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card_box.set_size_request(300, 300) 
        card_box.add_css_class("card")
        card_box.name = name
        
        # Image Container (Top Section)
        image_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        image_container.set_size_request(-1,-1)
        image_container.add_css_class("card-image-container")
        
        # Carrier Icon Loading
        icon_name = self.tracker.CARRIER_ICONS.get(courier, "package")
        try:
            icon_path = os.path.join(self.icons_dir, icon_name + ".png")
            print("Looking for icon at:", icon_path)
            print("FLATPAK_SANDBOX =", os.environ.get("FLATPAK_SANDBOX"))
            if os.path.exists(icon_path):
                # Load and scale courier logos to fit the container
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 200, 100, True)
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                courier_icon = Gtk.Picture.new_for_paintable(texture)
                courier_icon.set_size_request(240,110)
            else:
                raise FileNotFoundError(f"Courier icon not found: {icon_path}")

            courier_icon.set_halign(Gtk.Align.CENTER)
            courier_icon.set_valign(Gtk.Align.CENTER)
            image_container.append(courier_icon)
            
        except Exception as e:
            self.log_message(f"⚠️ Error loading icon for {courier}: {e}")
            # Fallback to package icon
            fallback_icon = Gtk.Image.new_from_icon_name(IconHelper.get_icon_name("package"))
            fallback_icon.set_pixel_size(64)
            fallback_icon.set_halign(Gtk.Align.CENTER)
            fallback_icon.set_valign(Gtk.Align.CENTER)
            image_container.append(fallback_icon)
        
        card_box.append(image_container)

        # Content Container (Middle Section)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(10)
        
        # Shipment name with ellipsis
        title_label = Gtk.Label(label=name, xalign=0, wrap=True, max_width_chars=20, ellipsize=Pango.EllipsizeMode.END)
        title_label.add_css_class("card-title")
        card_box.title_label = title_label
        content_box.append(title_label)

        # Tracking number
        number_label = Gtk.Label(label=number, xalign=0)
        number_label.add_css_class("card-subtitle")
        card_box.number_label = number_label
        content_box.append(number_label)

        # Progress bar
        progress_bar = Gtk.ProgressBar()
        progress_fraction = 1.0 if last_status == TrackEventStatusCode.DELIVERED else 0.25
        progress_bar.set_fraction(progress_fraction)
        progress_bar.set_margin_top(8)
        progress_bar.add_css_class("card-progress")
        card_box.progress_bar = progress_bar
        content_box.append(progress_bar)
        
        card_box.append(content_box)

        # Action Buttons (Bottom Section)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        button_box.set_homogeneous(True)  # Equal width buttons
        button_box.add_css_class("card-actions")
        button_box.set_spacing(10)
        button_box.set_margin_start(10)
        button_box.set_margin_end(10)
        button_box.set_margin_bottom(10)
        button_box.set_margin_top(0)
        
        
        # Details button (Blue)
        details_button = Gtk.Button(icon_name="view-more-horizontal-symbolic")
        details_button.add_css_class("details-button")
        details_button.set_tooltip_text("View Details")
        details_button.connect("clicked", lambda b: self.start_tracking(name, number, courier, show_results_page=True))
        button_box.append(details_button)
        
        # Track button (Purple)
        track_button = Gtk.Button(icon_name="web-browser-symbolic")
        track_button.add_css_class("track-button")
        track_button.set_tooltip_text("Open Tracking Link")
        track_button.connect("clicked", lambda b: self.open_tracking_link(b, self.tracker.CARRIERS.get(courier), number))
        button_box.append(track_button)
        
        card_box.append(button_box)

        # Store required labels for updates
        card_box.status_label = Gtk.Label()  # Hidden label to store status
        card_box.courier_label = Gtk.Label()  # Hidden label to store courier
        card_box.days_in_transit_label = Gtk.Label()  # Hidden label to store days in transit
        
        self.parcel_cards[number] = card_box
        return card_box


# ---------------- Application ----------------
class ParcelApp(Adw.Application):
    def __init__(self, **kwargs): 
        super().__init__(application_id="io.github.astoko.ParcelBuddy", **kwargs)
        print("⚙️ Initializing ParcelApp...")
        
        # Set up icon theme paths
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        # Add our custom icons directory to the search path
        app_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(app_dir, "icons")
        icon_theme.add_search_path(icons_dir)
        
        # Also add material icons if they exist in common locations
        potential_icon_paths = [
            "/usr/share/parcelapp/icons/material",
            "/usr/local/share/parcelapp/icons/material",
            os.path.expanduser("~/.local/share/parcelapp/icons/material")
        ]
        for path in potential_icon_paths:
            if os.path.exists(path):
                icon_theme.add_search_path(path)

        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        GRAPHQL_URL = os.getenv("GRAPHQL_URL")
        
        if CLIENT_ID:
            print("Found CLient ID")
        else:
            print("Nope no client ID")
        self.connect('activate', self.on_activate)
        self.connect('shutdown', self.on_shutdown)
        print("✅ ParcelApp initialized.")

    def on_activate(self, app):
        print("🚀 Application activating...")
        if not hasattr(self, 'win') or not self.win:
            self.win = ParcelWindow(application=app)
            print("✅ Main window created.")

        # Check credentials
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        GRAPHQL_URL = os.getenv("GRAPHQL_URL")

        if not CLIENT_ID or not CLIENT_SECRET or not GRAPHQL_URL:
            self.win.stack.set_visible_child_name("onboarding")
            self.win.log_message("↔️ No API credentials found, showing onboarding page.")
            # DO NOT run parcel updates until credentials are provided
        else:
            self.win.stack.set_visible_child_name("dashboard")
            self.win.log_message("↔️ Credentials found, showing dashboard page.")
            self.win.check_for_updates()
            self.win.update_source_id = GLib.timeout_add(1000, self.win.update_countdown_label)

        # <-- ADD THIS LINE
        self.win.present()


        # --- NEW & IMPROVED CSS STYLING ---
        css = """
        @define-color brand_primary #6200EE;
        @define-color brand_secondary #03DAC6;
        @define-color card_success #4caf50;
        @define-color card_accent #3b82f6;
        @define-color card_warning #ffb74d;
        @define-color card_error #f44336;
        @define-color card_unknown #808080;
        
        @keyframes fade-in {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* General UI improvements */
        AdwHeaderBar {
            background: linear-gradient(to right, @brand_primary, @brand_secondary);
            color: white;
            padding: 10px;
        }

        AdwHeaderBar GtkButton {
            color: white;
        }
        
        GtkSearchEntry {
            border-radius: 20px;
            background-color: alpha(white, 0.2);
            padding: 5px 15px;
            color: white;
        }

        /* Base card style */
        .card {
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin: 10px;
            animation: fade-in 0.5s ease-out;
            transition: box-shadow 0.3s ease-in-out, transform 0.2s ease-in-out;
        }
        
        .card:hover {
            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
            transform: translateY(-5px);
        }

        /* Dark Mode Color Adjustments */
        @media (prefers-color-scheme: dark) {
            .card {
                background-color: #2e2e2e;
                border: 1px solid #444;
            }
            .card.delivered { border-bottom: 5px solid @card_success; }
            .card.intransit { border-bottom: 5px solid @card_accent; }
            .card.outfordelivery { border-bottom: 5px solid @card_accent; }
            .card.pickup { border-bottom: 5px solid @card_warning; }
            .card.exception { border-bottom: 5px solid @card_error; }
            .card.unknown { border-bottom: 5px solid @card_unknown; }
            
            .timeline-container { border-left: 2px solid #444; }
            .timeline-icon-circle { background-color: #2e2e2e; border: 2px solid; }
            .timeline-icon-circle GtkImage { color: #fff; }
        }
        
        /* Light Mode Color Adjustments */
        @media (prefers-color-scheme: light) {
            .card {
                background-color: #fcfcfc;
                border: 1px solid #e0e0e0;
            }
            .card.delivered { border-bottom: 5px solid @card_success; }
            .card.intransit { border-bottom: 5px solid @card_accent; }
            .card.outfordelivery { border-bottom: 5px solid @card_accent; }
            .card.pickup { border-bottom: 5px solid @card_warning; }
            .card.exception { border-bottom: 5px solid @card_error; }
            .card.unknown { border-bottom: 5px solid @card_unknown; }
            
            .timeline-container { border-left: 2px solid #e0e0e0; }
            .timeline-icon-circle { background-color: #fcfcfc; border: 2px solid; }
            .timeline-icon-circle GtkImage { color: #000; }
        }

        /* Progress bar color */
        .card-progress.delivered { color: @card_success; }
        .card-progress.outfordelivery { color: @card_accent; }
        .card-progress.intransit { color: @card_accent; }
        .card-progress.pickup { color: @card_warning; }
        .card-progress.exception { color: @card_error; }
        .card-progress.unknown { color: @card_unknown; }
        .card-progress { min-height: 5px; }

        /* Timeline styles */
        .timeline-container {
            margin-left: 10px;
            padding-left: 20px;
        }
        
        .timeline-event-vbox {
            margin-left: -32px;
            margin-right: 12px;
        }

        .timeline-icon-circle {
            border-radius: 50%;
            width: 20px;
            height: 20px;
            padding: 2px;
            transition: all 0.2s ease;
        }
        
        .timeline-event-vbox.delivered .timeline-icon-circle { border-color: @card_success; }
        .timeline-event-vbox.intransit .timeline-icon-circle { border-color: @card_accent; }
        .timeline-event-vbox.outfordelivery .timeline-icon-circle { border-color: @card_accent; }
        .timeline-event-vbox.pickup .timeline-icon-circle { border-color: @card_warning; }
        .timeline-event-vbox.exception .timeline-icon-circle { border-color: @card_error; }
        .timeline-event-vbox.unknown .timeline-icon-circle { border-color: @card_unknown; }
        
        /* Other styles */
        .dim-label { opacity: 0.5; }
        .caption { font-size: small; }
        .card-title { font-size: x-large; font-weight: bold; }
        .status-label { font-size: medium; font-weight: bold; }
        
        .timer-label {
            font-weight: bold;
            font-size: 1.2em;
        }
        .flat {
            background-color: transparent;
            border: none;
        }
        
        .suggested-action {
            background-image: linear-gradient(to bottom, #4c9aff, #3b82f6);
            color: white;
            border: none;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.2s ease-in-out;
        }
        
        .suggested-action:hover {
            background-image: linear-gradient(to bottom, #3b82f6, #2563eb);
            box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
        }

        .destructive-action {
            color: @card_error;
        }

        .details-button {
            color: @card_accent;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        print("🎨 CSS styles loaded.")

    def on_shutdown(self, app):
        print("🛑 Shutting down application...")
        if hasattr(self, 'win') and self.win.update_source_id:
            GLib.source_remove(self.win.update_source_id)

if __name__ == "__main__":
    app = ParcelApp()
    app.run(sys.argv)
