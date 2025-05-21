import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.10/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, onAuthStateChanged, signOut, setPersistence, browserLocalPersistence } from "https://www.gstatic.com/firebasejs/9.6.10/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAqkv5oLDIvuhBUXFqfxp69QDsBjyqmuNk",
  authDomain: "planscape-1d647.firebaseapp.com",
  projectId: "planscape-1d647",
  storageBucket: "planscape-1d647.firebasestorage.app",
  messagingSenderId: "188770733819",
  appId: "1:188770733819:web:9412d8240ddc6478e6ea5e"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Set persistence to LOCAL to ensure login state is saved
setPersistence(auth, browserLocalPersistence)
  .then(() => {
    console.log("Firebase auth persistence set to LOCAL");
  })
  .catch((error) => {
    console.error("Error setting Firebase persistence:", error.message);
  });

// Export auth for use in other scripts
export { auth };

// Variable to track the last auth action
let lastAuthAction = null;

// Handle signup
export function signup(email, password) {
  lastAuthAction = 'signup';
  return createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      console.log("Signup successful:", user);
      return user;
    })
    .catch((error) => {
      console.error("Signup error:", error.code, error.message);
      throw error;
    });
}

// Handle login
export function login(email, password) {
  lastAuthAction = 'login';
  return signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      console.log("Login successful:", user);
      return user;
    })
    .catch((error) => {
      console.error("Login error:", error.code, error.message);
      throw error;
    });
}

// Handle logout
export function logout() {
  lastAuthAction = 'logout';
  signOut(auth)
    .then(() => {
      console.log("Logout successful");
      window.location.href = "/login";
    })
    .catch((error) => {
      console.error("Logout error:", error.message);
    });
}

// Monitor auth state changes
onAuthStateChanged(auth, (user) => {
  const currentPath = window.location.pathname;
  console.log("onAuthStateChanged triggered:", { user: user ? user.uid : null, currentPath, lastAuthAction });

  if (user) {
    // User is signed in
    user.getIdToken(true)  // Force refresh the token to ensure it's valid
      .then((idToken) => {
        fetch("/set_session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ idToken: idToken }), // Send idToken, not uid
        })
          .then((response) => {
            if (!response.ok) {
              return response.text().then((text) => {
                throw new Error(`Server returned ${response.status}: ${text}`);
              });
            }
            return response.json();
          })
          .then((data) => {
            if (data.status === "success") {
              console.log("Session set successfully in Flask");
              // Redirect to /success only if the last action was login and we're on /login
              if (lastAuthAction === 'login' && currentPath === "/login") {
                console.log("Redirecting to /success due to recent login");
                lastAuthAction = null; // Reset the action to prevent further redirects
                window.location.href = `/success?action=login`;
              } else if (lastAuthAction === 'signup' && currentPath === "/signup") {
                // After signup, allow the redirect to /login from signup.html
                console.log("Signup detected, allowing redirect to /login from signup.html");
                lastAuthAction = null; // Reset the action
              } else if (lastAuthAction === 'logout') {
                // Do nothing after logout; the logout function already handles the redirect
                lastAuthAction = null;
              } else if (currentPath === "/success") {
                // If already on /success, do not redirect further
                console.log("Already on /success, no further redirect needed");
                lastAuthAction = null;
              } else if (currentPath !== "/signup" && currentPath !== "/login") {
                // Redirect to /planner only if not on signup/login/success pages and no recent auth action
                console.log("Redirecting to /planner as user is signed in and not on auth pages");
                window.location.href = "/planner";
              }
            } else {
              console.error("Failed to set session:", data.message);
              auth.signOut();
              window.location.href = "/login";
            }
          })
          .catch((error) => {
            console.error("Error setting session:", error.message);
            auth.signOut();
            window.location.href = "/login";
          });
      })
      .catch((error) => {
        console.error("Error getting ID token:", error.message);
        auth.signOut();
        window.location.href = "/login";
      });
  } else {
    // No user is signed in
    console.log("No user is signed in");
    if (currentPath !== "/signup" && currentPath !== "/login" && currentPath !== "/success") {
      window.location.href = "/login";
    }
    lastAuthAction = null; // Reset the action when user is signed out
  }
});
