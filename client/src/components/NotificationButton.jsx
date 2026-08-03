import React, { useState, useEffect } from 'react';
import { Bell, BellOff } from 'lucide-react';
import { apiCall } from '../services/api';

const urlB64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
};

const NotificationButton = () => {
    const [isSubscribed, setIsSubscribed] = useState(false);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        checkSubscription();
    }, []);

    const checkSubscription = async () => {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            const subscription = await registration.pushManager.getSubscription();
            setIsSubscribed(!!subscription);
        } catch (error) {
            console.error('Service Worker Error', error);
        }
    };

    const subscribeUser = async () => {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            alert('Push notifications not supported by your browser.');
            return;
        }

        setLoading(true);
        try {
            // Register Service Worker
            const registration = await navigator.serviceWorker.register('/sw.js');

            // Get VAPID public key from server
            const { public_key } = await apiCall('/api/push/vapid-public-key');
            const applicationServerKey = urlB64ToUint8Array(public_key);

            // Subscribe user
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey
            });

            // Send subscription to backend
            await apiCall('/api/push/subscribe', {
                method: 'POST',
                body: JSON.stringify(subscription)
            });

            setIsSubscribed(true);
        } catch (error) {
            console.error('Failed to subscribe to push notifications:', error);
            if (Notification.permission === 'denied') {
                alert('Please allow notification permission in your browser.');
            } else {
                alert('An error occurred during subscription setup.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <button 
            onClick={subscribeUser} 
            disabled={isSubscribed || loading}
            className={`btn-icon ${isSubscribed ? 'text-green-400' : 'text-gray-300'}`}
            title={isSubscribed ? 'Notifications Disabled' : 'Enable Push Notifications'}
        >
            {isSubscribed ? <Bell size={20} /> : <BellOff size={20} />}
        </button>
    );
};

export default NotificationButton;
