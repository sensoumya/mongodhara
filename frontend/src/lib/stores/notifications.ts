import { writable } from "svelte/store";

export type NotificationType = "success" | "error";

export interface Notification {
  id: number;
  message: string;
  type: NotificationType;
}

// Create a writable store for notifications
export const notifications = writable<Notification[]>([]);

// Function to add a new notification
export function addNotification(message: string, type: NotificationType) {
  const id = Date.now();
  notifications.update((currentNotifications) => [
    ...currentNotifications,
    { id, message, type },
  ]);

  // Automatically remove the notification after a few seconds
  setTimeout(() => {
    removeNotification(id);
  }, 5000);
}

// Function to remove a notification by its ID
export function removeNotification(id: number) {
  notifications.update((currentNotifications) =>
    currentNotifications.filter((n) => n.id !== id)
  );
}
