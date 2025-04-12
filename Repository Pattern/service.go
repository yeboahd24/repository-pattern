package main

import (
	"math/rand"
	"time"
)

// Service interface
type Service interface {
	GetAll() ([]*User, error)
	GetByID(id string) (*User, error)
	Create(name, email string) error
	Update(user *User) error
	Delete(id string) error
}

// Service implementation
type userService struct {
	repo Repository
}

// Factory function to create a new userService
func NewUserService(repo Repository) Service {
	return &userService{repo: repo}
}

// Implementation of Service interface methods
func (s *userService) GetAll() ([]*User, error) {
	return s.repo.GetAll()
}

func (s *userService) GetByID(id string) (*User, error) {
	return s.repo.GetByID(id)
}

func (s *userService) Create(name, email string) error {
	user := &User{Name: name, Email: email, CreatedAt: time.Now(), ID: generateID()}
	return s.repo.Create(user)
}

func (s *userService) Update(user *User) error {
	return s.repo.Update(user)
}

func (s *userService) Delete(id string) error {
	return s.repo.Delete(id)
}

// random generate ID
func generateID() int {
	return rand.Intn(1000000)
}
