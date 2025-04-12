package main

import (
	"database/sql"
	"fmt"
	"net/http"

	_ "github.com/lib/pq"
)

func main() {

	// Create a new configuration instance
	config := NewConfig()

	fmt.Println(config.GetConnectionString())

	// Create a new database connection using the configuration
	fmt.Println("Attempting to connect to database with connection string:")
	fmt.Println(config.GetConnectionString())

	db, err := sql.Open("postgres", config.GetConnectionString())
	if err != nil {
		fmt.Println("Error opening database connection:", err)
		fmt.Println("Using mock database instead")
		// Create a mock repository for demonstration purposes
		repo := createMockRepository()
		service := NewUserService(repo)
		handler := NewHandler(service)

		// Define routes and their corresponding handlers
		http.HandleFunc("/users", handler.GetAllUsers)
		http.HandleFunc("/users/create", handler.CreateUser)
		http.HandleFunc("/users/update", handler.UpdateUser)
		http.HandleFunc("/users/delete", handler.DeleteUser)

		// Start the server
		fmt.Println("Server started on :8080")
		http.ListenAndServe(":8080", nil)
		return
	}
	defer db.Close()

	// Check the database connection
	err = db.Ping()
	if err != nil {
		fmt.Println("Error pinging database:", err)
		fmt.Println("Using mock database instead")
		// Create a mock repository for demonstration purposes
		repo := createMockRepository()
		service := NewUserService(repo)
		handler := NewHandler(service)

		// Define routes and their corresponding handlers
		http.HandleFunc("/users", handler.GetAllUsers)
		http.HandleFunc("/users/create", handler.CreateUser)
		http.HandleFunc("/users/update", handler.UpdateUser)
		http.HandleFunc("/users/delete", handler.DeleteUser)

		// Start the server
		fmt.Println("Server started on :8080")
		http.ListenAndServe(":8080", nil)
		return
	}

	// Create a new repository instance (production)
	repo := NewUserRepository(db)

	// Create a new service instance using the repository
	service := NewUserService(repo)

	// Create a new handler instance using the service
	handler := NewHandler(service)

	// Define routes and their corresponding handlers
	http.HandleFunc("/users", handler.GetAllUsers)
	http.HandleFunc("/users/create", handler.CreateUser)
	http.HandleFunc("/users/update", handler.UpdateUser)
	http.HandleFunc("/users/delete", handler.DeleteUser)

	// Start the server
	fmt.Println("Server started on :8080")
	http.ListenAndServe(":8080", nil)
}
