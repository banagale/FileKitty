"""
Pytest configuration and fixtures for FileKitty tests.

This module provides shared fixtures and test utilities used across all test modules.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''
"""Module docstring."""

import os
import sys
from pathlib import Path

CONSTANT = 42

class MyClass:
    """Class docstring."""

    def __init__(self):
        self.value = 0

    def my_method(self, arg):
        """Method docstring."""
        return arg * 2

class AnotherClass(MyClass):
    """Another class."""
    pass

def my_function(x, y):
    """Function docstring."""
    return x + y

async def async_function():
    """Async function."""
    await some_task()

def _private_function():
    """Private function."""
    pass
'''


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return '''
// JavaScript test file

import { something } from './module';
import React from 'react';

const CONSTANT = 42;

function myFunction(x, y) {
    return x + y;
}

const arrowFunction = (x) => x * 2;

async function asyncFunction() {
    await fetch('/api');
}

class MyClass {
    constructor() {
        this.value = 0;
    }

    myMethod(arg) {
        return arg * 2;
    }

    static staticMethod() {
        return 'static';
    }
}

export { myFunction, MyClass };
export default arrowFunction;
'''


@pytest.fixture
def sample_typescript_code():
    """Sample TypeScript code for testing."""
    return '''
// TypeScript test file

import { Component } from 'react';

interface User {
    id: number;
    name: string;
}

type UserID = number;

enum Status {
    Active,
    Inactive,
    Pending
}

class UserService {
    private users: User[] = [];

    public async getUser(id: UserID): Promise<User | null> {
        return this.users.find(u => u.id === id) || null;
    }

    protected validateUser(user: User): boolean {
        return user.id > 0;
    }
}

export function createUser(name: string): User {
    return { id: Date.now(), name };
}

export { UserService, Status };
export type { User, UserID };
'''


@pytest.fixture
def sample_go_code():
    """Sample Go code for testing."""
    return '''
package main

import (
    "fmt"
    "net/http"
)

// Constant comment
const MaxRetries = 3

// User represents a user in the system
type User struct {
    ID   int
    Name string
}

// Server handles HTTP requests
type Server struct {
    port int
}

// NewServer creates a new server instance
func NewServer(port int) *Server {
    return &Server{port: port}
}

// Start starts the server
func (s *Server) Start() error {
    return http.ListenAndServe(fmt.Sprintf(":%d", s.port), nil)
}

// HandleRequest processes an HTTP request
func (s *Server) HandleRequest(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello, World!")
}

// privateFunction is not exported
func privateFunction() {
    fmt.Println("private")
}

// PublicFunction is exported
func PublicFunction() {
    fmt.Println("public")
}
'''


@pytest.fixture
def sample_rust_code():
    """Sample Rust code for testing."""
    return '''
use std::fmt;

const MAX_RETRIES: u32 = 3;

pub struct User {
    pub id: u32,
    pub name: String,
}

impl User {
    pub fn new(id: u32, name: String) -> Self {
        User { id, name }
    }

    pub fn greet(&self) -> String {
        format!("Hello, {}!", self.name)
    }

    fn validate(&self) -> bool {
        !self.name.is_empty()
    }
}

pub trait Greeter {
    fn greet(&self) -> String;
}

impl Greeter for User {
    fn greet(&self) -> String {
        self.greet()
    }
}

pub enum Status {
    Active,
    Inactive,
    Pending,
}

pub fn create_user(id: u32, name: String) -> User {
    User::new(id, name)
}

fn private_function() -> i32 {
    42
}

pub async fn async_function() -> Result<(), String> {
    Ok(())
}
'''


@pytest.fixture
def sample_java_code():
    """Sample Java code for testing."""
    return '''
package com.example.app;

import java.util.List;
import java.util.ArrayList;

public class User {
    private int id;
    private String name;

    public User(int id, String name) {
        this.id = id;
        this.name = name;
    }

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    private boolean validate() {
        return name != null && !name.isEmpty();
    }
}

public interface UserRepository {
    User findById(int id);
    List<User> findAll();
    void save(User user);
}

public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}

public class UserService {
    private UserRepository repository;

    public UserService(UserRepository repository) {
        this.repository = repository;
    }

    public User getUser(int id) {
        return repository.findById(id);
    }

    protected void validateUser(User user) {
        if (!user.validate()) {
            throw new IllegalArgumentException("Invalid user");
        }
    }
}
'''


@pytest.fixture
def sample_ruby_code():
    """Sample Ruby code for testing."""
    return '''
module MyModule
  CONSTANT = 42

  def self.module_method
    "module method"
  end
end

class User
  attr_reader :id, :name
  attr_writer :email

  def initialize(id, name)
    @id = id
    @name = name
  end

  def greet
    "Hello, #{@name}!"
  end

  private

  def validate
    !@name.nil? && !@name.empty?
  end
end

class AdminUser < User
  def admin_action
    "admin stuff"
  end
end

def public_function(x, y)
  x + y
end

def private_function
  "private"
end
'''


@pytest.fixture
def sample_cpp_code():
    """Sample C++ code for testing."""
    return '''
#include <iostream>
#include <string>
#include <vector>

namespace app {

const int MAX_SIZE = 100;

class User {
private:
    int id;
    std::string name;

public:
    User(int id, const std::string& name) : id(id), name(name) {}

    int getId() const { return id; }
    std::string getName() const { return name; }

    virtual void greet() {
        std::cout << "Hello, " << name << std::endl;
    }

private:
    bool validate() {
        return !name.empty();
    }
};

class AdminUser : public User {
public:
    AdminUser(int id, const std::string& name) : User(id, name) {}

    void adminAction() {
        std::cout << "Admin action" << std::endl;
    }
};

struct Point {
    int x;
    int y;
};

enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
};

int add(int a, int b) {
    return a + b;
}

static int privateFunction() {
    return 42;
}

} // namespace app
'''


@pytest.fixture
def sample_php_code():
    """Sample PHP code for testing."""
    return '''
<?php

namespace App\\Model;

use App\\Repository\\UserRepository;

interface UserInterface {
    public function getId(): int;
    public function getName(): string;
}

trait Timestampable {
    private $createdAt;
    private $updatedAt;

    public function getCreatedAt() {
        return $this->createdAt;
    }
}

class User implements UserInterface {
    use Timestampable;

    private int $id;
    private string $name;
    protected string $email;

    public function __construct(int $id, string $name) {
        $this->id = $id;
        $this->name = $name;
    }

    public function getId(): int {
        return $this->id;
    }

    public function getName(): string {
        return $this->name;
    }

    protected function validate(): bool {
        return !empty($this->name);
    }

    private function privateMethod() {
        return "private";
    }
}

abstract class BaseService {
    abstract public function process();
}

final class UserService extends BaseService {
    private UserRepository $repository;

    public function __construct(UserRepository $repository) {
        $this->repository = $repository;
    }

    public function process() {
        // Implementation
    }
}

function createUser(string $name): User {
    return new User(time(), $name);
}
'''


@pytest.fixture
def sample_csharp_code():
    """Sample C# code for testing."""
    return '''
using System;
using System.Collections.Generic;
using System.Linq;

namespace App.Models
{
    public interface IUser
    {
        int Id { get; }
        string Name { get; }
    }

    public struct Point
    {
        public int X { get; set; }
        public int Y { get; set; }
    }

    public enum Status
    {
        Active,
        Inactive,
        Pending
    }

    public class User : IUser
    {
        private int id;
        private string name;

        public int Id => id;
        public string Name => name;

        public User(int id, string name)
        {
            this.id = id;
            this.name = name;
        }

        public string Greet()
        {
            return $"Hello, {name}!";
        }

        protected virtual bool Validate()
        {
            return !string.IsNullOrEmpty(name);
        }

        private void PrivateMethod()
        {
            // Private implementation
        }
    }

    public class AdminUser : User
    {
        public AdminUser(int id, string name) : base(id, name) { }

        public async Task<string> AdminActionAsync()
        {
            await Task.Delay(100);
            return "admin action";
        }
    }

    public static class UserHelper
    {
        public static User CreateUser(string name)
        {
            return new User(DateTime.Now.Millisecond, name);
        }
    }
}
'''


@pytest.fixture
def sample_bash_code():
    """Sample Bash code for testing."""
    return '''
#!/bin/bash

# Constants
readonly MAX_RETRIES=3
readonly LOG_FILE="/var/log/app.log"

# Simple function
function simple_function() {
    echo "Hello, World!"
}

# Function with arguments
function process_file() {
    local file="$1"
    local output="$2"

    if [[ -f "$file" ]]; then
        cat "$file" > "$output"
        return 0
    else
        echo "File not found: $file" >&2
        return 1
    fi
}

# Function with validation
validate_input() {
    if [[ -z "$1" ]]; then
        echo "Error: No input provided" >&2
        return 1
    fi
    return 0
}

# Main function
main() {
    local arg="$1"

    if validate_input "$arg"; then
        process_file "$arg" "/tmp/output.txt"
    fi
}

# Private function convention
_private_helper() {
    echo "This is private by convention"
}

main "$@"
'''


@pytest.fixture
def create_test_file(temp_dir):
    """Factory fixture for creating test files."""
    def _create_file(filename: str, content: str) -> Path:
        file_path = temp_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path
    return _create_file
