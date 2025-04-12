package main

import "database/sql"

// Repository interface
type Repository interface {
	GetAll() ([]*User, error)
	GetByID(id string) (*User, error)
	Create(user *User) error
	Update(user *User) error
	Delete(id string) error
}

type userRepository struct {
	// Database connection
	db *sql.DB
}

// Factory function to create a new userRepository
func NewUserRepository(db *sql.DB) Repository {
	return &userRepository{db: db}
}

// Implementation of Repository interface methods
func (r *userRepository) GetAll() ([]*User, error) {
	// Implementation to fetch all users from the database
	query := "SELECT * FROM test_users"
	rows, err := r.db.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Process rows and create []*User slice
	users := make([]*User, 0)
	for rows.Next() {
		user := &User{}
		err := rows.Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)
		if err != nil {
			return nil, err
		}
		users = append(users, user)
	}

	return users, nil

}

func (r *userRepository) GetByID(id string) (*User, error) {
	// Implementation to fetch a user by ID from the database
	query := "SELECT * FROM test_users WHERE id = $1"
	row := r.db.QueryRow(query, id)
	user := &User{}
	err := row.Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)
	if err != nil {
		return nil, err
	}
	return user, nil
}

func (r *userRepository) Create(user *User) error {
	// Implementation to create a new user in the database
	query := "INSERT INTO test_users (id, name, email, created_at) VALUES ($1, $2, $3, $4)"
	_, err := r.db.Exec(query, user.ID, user.Name, user.Email, user.CreatedAt)
	if err != nil {
		return err
	}
	return nil
}

func (r *userRepository) Update(user *User) error {
	// Implementation to update an existing user in the database
	query := "UPDATE test_users SET name = $1, email = $2 WHERE id = $3"
	_, err := r.db.Exec(query, user.Name, user.Email, user.ID)
	if err != nil {
		return err
	}
	return nil
}

func (r *userRepository) Delete(id string) error {
	// Implementation to delete a user from the database
	query := "DELETE FROM test_users WHERE id = $1"
	_, err := r.db.Exec(query, id)
	if err != nil {
		return err
	}
	return nil
}
