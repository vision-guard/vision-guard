self.addEventListener('push', function(event) {
    if (event.data) {
        const payload = event.data.json();
        const options = {
            body: payload.body,
            icon: payload.icon || '/vite.svg',
            badge: payload.badge || '/vite.svg',
            vibrate: [200, 100, 200, 100, 200, 100, 200],
            actions: [
                {
                    action: 'view',
                    title: 'View Alert'
                }
            ],
            data: {
                dateOfArrival: Date.now(),
                url: payload.url || '/'
            }
        };

        const title = payload.title || 'Vision Guard Alert';
        event.waitUntil(
            self.registration.showNotification(title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    const urlToOpen = event.notification.data.url;
    
    if (event.action === 'view' || !event.action) {
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
                for (let i = 0; i < windowClients.length; i++) {
                    const client = windowClients[i];
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
        );
    }
});
