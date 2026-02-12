/**
 * WebAuthn Helper Service
 * Handles browser-side biometric (Fingerprint/FaceID) operations
 */

/* global PublicKeyCredential */
import axios from 'axios';

/**
 * Convert base64url string to Uint8Array
 */
function base64urlToUint8Array(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4;
    const padded = pad ? base64 + '='.repeat(4 - pad) : base64;
    const binary = window.atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

/**
 * Convert Uint8Array to base64url string
 */
function uint8ArrayToBase64url(bytes) {
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

/**
 * Check if the current browser/device supports platform biometrics
 */
export async function isBiometricAvailable() {
    if (window.PublicKeyCredential &&
        PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable) {
        return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    }
    return false;
}

/**
 * Register a new biometric credential
 */
export async function registerBiometric() {
    const token = localStorage.getItem('authToken');

    // 1. Get options from server
    const optionsRes = await axios.get('/api/biometric/register/options', {
        headers: { Authorization: `Bearer ${token}` }
    });

    const options = optionsRes.data;

    // 2. Prepare options for create()
    options.challenge = base64urlToUint8Array(options.challenge);
    options.user.id = base64urlToUint8Array(options.user.id);

    if (options.excludeCredentials) {
        for (let cred of options.excludeCredentials) {
            cred.id = base64urlToUint8Array(cred.id);
        }
    }

    // 3. Trigger browser biometric prompt
    const credential = await navigator.credentials.create({
        publicKey: options
    });

    // 4. Prepare response for server verification
    const credentialJson = {
        id: credential.id,
        rawId: uint8ArrayToBase64url(new Uint8Array(credential.rawId)),
        type: credential.type,
        response: {
            attestationObject: uint8ArrayToBase64url(new Uint8Array(credential.response.attestationObject)),
            clientDataJSON: uint8ArrayToBase64url(new Uint8Array(credential.response.clientDataJSON)),
        }
    };

    // 5. Send to server for verification
    return await axios.post('/api/biometric/register/verify', credentialJson, {
        headers: { Authorization: `Bearer ${token}` }
    });
}

/**
 * Authenticate using biometric credential
 */
export async function authenticateBiometric(userId) {
    // 1. Get options from server
    const optionsRes = await axios.get(`/api/biometric/authenticate/options/${userId}`);
    const options = optionsRes.data;

    // 2. Prepare options for get()
    options.challenge = base64urlToUint8Array(options.challenge);

    if (options.allowCredentials) {
        for (let cred of options.allowCredentials) {
            cred.id = base64urlToUint8Array(cred.id);
        }
    }

    // 3. Trigger browser biometric prompt
    const assertion = await navigator.credentials.get({
        publicKey: options
    });

    // 4. Prepare response for server verification
    const assertionJson = {
        id: assertion.id,
        rawId: uint8ArrayToBase64url(new Uint8Array(assertion.rawId)),
        type: assertion.type,
        response: {
            authenticatorData: uint8ArrayToBase64url(new Uint8Array(assertion.response.authenticatorData)),
            clientDataJSON: uint8ArrayToBase64url(new Uint8Array(assertion.response.clientDataJSON)),
            signature: uint8ArrayToBase64url(new Uint8Array(assertion.response.signature)),
            userHandle: assertion.response.userHandle ? uint8ArrayToBase64url(new Uint8Array(assertion.response.userHandle)) : null,
        }
    };

    // 5. Send to server for verification and final login
    return await axios.post(`/api/biometric/authenticate/verify/${userId}`, assertionJson);
}
