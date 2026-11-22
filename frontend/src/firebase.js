
import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBwtehvIwKqj0REbSfeZFSK-3rotFeb6t0",
  authDomain: "smart-healthguard.firebaseapp.com",
  projectId: "smart-healthguard",
  storageBucket: "smart-healthguard.firebasestorage.app",
  messagingSenderId: "891245154762",
  appId: "1:891245154762:web:5dab8ca403f739818f3f33",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export {
  signInWithPopup,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged,
};
