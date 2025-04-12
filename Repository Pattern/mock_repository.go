package main

import (
	"time"
)

// Mock repository implementation
type mockUserRepository struct {
	users []*User
}

// Factory function to create a new mockUserRepository
func createMockRepository() Repository {
	// Create some mock users
	users := []*User{
		{ID: 1, Name: "John Doe", Email: "john@example.com", CreatedAt: time.Now()},
		{ID: 2, Name: "Jane Smith", Email: "jane@example.com", CreatedAt: time.Now()},
	}
	return &mockUserRepository{users: users}
}

// Implementation of Repository interface methods
func (r *mockUserRepository) GetAll() ([]*User, error) {
	return r.users, nil
}

func (r *mockUserRepository) GetByID(id string) (*User, error) {
	for _, user := range r.users {
		if string(rune(user.ID)) == id {
			return user, nil
		}
	}
	return nil, nil
}

func (r *mockUserRepository) Create(user *User) error {
	r.users = append(r.users, user)
	return nil
}

func (r *mockUserRepository) Update(user *User) error {
	for i, u := range r.users {
		if u.ID == user.ID {
			r.users[i] = user
			return nil
		}
	}
	return nil
}

func (r *mockUserRepository) Delete(id string) error {
	for i, user := range r.users {
		if string(rune(user.ID)) == id {
			r.users = append(r.users[:i], r.users[i+1:]...)
			return nil
		}
	}
	return nil
}
